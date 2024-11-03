from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.config import settings
from app.players.enums import PlayerGamemode, PlayerPlatform
from tests.helpers import read_json_file

platforms = {p.value for p in PlayerPlatform}
gamemodes = {g.value for g in PlayerGamemode}


@pytest.mark.parametrize(
    ("player_html_data", "gamemode", "platform"),
    [
        ("TeKrop-2217", gamemode, platform)
        for gamemode in (None, Mock(value="invalid_gamemode"), *PlayerGamemode)
        for platform in (None, Mock(value="invalid_platform"), *PlayerPlatform)
    ],
    indirect=["player_html_data"],
)
def test_get_player_stats(
    client: TestClient,
    player_html_data: str,
    gamemode: PlayerGamemode | None,
    platform: PlayerPlatform | None,
    player_search_response_mock: Mock,
):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        query_params = "&".join(
            [
                (f"gamemode={gamemode.value}" if gamemode else ""),
                (f"platform={platform.value}" if platform else ""),
            ],
        )
        params = f"?{query_params}" if any(query_params) else ""
        response = client.get(f"/players/TeKrop-2217/stats/summary{params}")

    if (gamemode and gamemode not in gamemodes) or (
        platform and platform not in platforms
    ):
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        assert response.status_code == status.HTTP_200_OK

        filtered_data = read_json_file(
            f"players/stats/filtered/TeKrop-2217-{gamemode}-{platform}.json",
        )
        assert response.json() == filtered_data


def test_get_player_stats_blizzard_error(client: TestClient):
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


def test_get_player_stats_blizzard_timeout(client: TestClient):
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


def test_get_player_stats_internal_error(client: TestClient):
    with patch(
        "app.players.controllers.get_player_stats_summary_controller.GetPlayerStatsSummaryController.process_request",
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


def test_get_player_stats_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}",
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }
