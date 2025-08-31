from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.config import settings
from app.players.enums import PlayerGamemode, PlayerPlatform


@pytest.fixture(autouse=True)
def _setup_player_stats_test(
    player_html_data: str,
    player_search_response_mock: Mock,
    blizzard_unlock_response_mock: Mock,
):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # UnlocksManager call
            blizzard_unlock_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        yield


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats(client: TestClient):
    response = client.get("/players/TeKrop-2217/stats/summary")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_valid_gamemode(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary",
        params={"gamemode": PlayerGamemode.QUICKPLAY},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_invalid_gamemode(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary",
        params={"gamemode": "invalid_gamemode"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_valid_platform(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary",
        params={"platform": PlayerPlatform.PC},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_empty_platform(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary",
        params={"platform": PlayerPlatform.CONSOLE},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_invalid_platform(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary",
        params={"platform": "invalid_platform"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get(
            "/players/TeKrop-2217/stats/summary",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_blizzard_timeout(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get(
            "/players/TeKrop-2217/stats/summary",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_internal_error(client: TestClient):
    with patch(
        "app.players.controllers.get_player_stats_summary_controller.GetPlayerStatsSummaryController.process_request",
        return_value={
            "general": [{"category": "invalid_value", "stats": [{"key": "test"}]}],
        },
    ):
        response = client.get(
            "/players/TeKrop-2217/stats/summary",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_stats_summary_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get(
            "/players/TeKrop-2217/stats/summary",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }
