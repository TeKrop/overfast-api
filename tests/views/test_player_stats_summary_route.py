from unittest.mock import Mock, patch

from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.common.enums import PlayerGamemode, PlayerPlatform


def test_get_player_stats(client: TestClient):
    response = client.get("/players/TeKrop-2217/stats/summary")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


def test_get_player_stats_summary_valid_gamemode(client: TestClient):
    response = client.get(
        f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


def test_get_player_stats_summary_invalid_gamemode(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary?gamemode=invalid_gamemode"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_player_stats_summary_valid_platform(client: TestClient):
    response = client.get(
        f"/players/TeKrop-2217/stats/summary?platform={PlayerPlatform.PC}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


def test_get_player_stats_summary_empty_platform(client: TestClient):
    response = client.get(
        f"/players/TeKrop-2217/stats/summary?platform={PlayerPlatform.CONSOLE}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_get_player_stats_summary_invalid_platform(client: TestClient):
    response = client.get(
        "/players/TeKrop-2217/stats/summary?platform=invalid_platform"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_player_stats_summary_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}",
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_player_stats_summary_blizzard_timeout(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}",
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


def test_get_player_stats_summary_internal_error(client: TestClient):
    with patch(
        "app.handlers.get_player_stats_summary_request_handler.GetPlayerStatsSummaryRequestHandler.process_request",
        return_value={
            "general": [{"category": "invalid_value", "stats": [{"key": "test"}]}],
        },
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}",
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
