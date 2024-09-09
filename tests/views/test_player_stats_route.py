from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.common.enums import HeroKeyCareerFilter, PlayerGamemode, PlayerPlatform


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_valid_hero(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}&hero={HeroKeyCareerFilter.ANA}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert set(response.json().keys()) == {HeroKeyCareerFilter.ANA}


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_invalid_hero(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}&hero=invalid_hero"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_missing_gamemode(client: TestClient, uri: str):
    response = client.get(f"/players/TeKrop-2217{uri}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_invalid_gamemode(client: TestClient, uri: str):
    response = client.get(f"/players/TeKrop-2217{uri}?gamemode=invalid_gamemode")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_valid_platform(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}&platform={PlayerPlatform.PC}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_empty_platform(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}&platform={PlayerPlatform.CONSOLE}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_invalid_platform(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}&platform=invalid_platform"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_blizzard_error(client: TestClient, uri: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}",
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_blizzard_timeout(client: TestClient, uri: str):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}",
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_internal_error(client: TestClient, uri: str):
    with patch(
        "app.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",
        return_value={
            "ana": [{"category": "invalid_value", "stats": [{"key": "test"}]}],
        },
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}?gamemode={PlayerGamemode.QUICKPLAY}",
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        }
