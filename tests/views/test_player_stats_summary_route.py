from unittest.mock import Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from overfastapi.common.enums import PlayerGamemode, PlayerPlatform
from overfastapi.common.helpers import read_json_file
from overfastapi.main import app

client = TestClient(app)
platforms = {p.value for p in PlayerPlatform}
gamemodes = {g.value for g in PlayerGamemode}


@pytest.mark.parametrize(
    "player_html_data,gamemode,platform",
    [
        ("TeKrop-2217", gamemode, platform)
        for gamemode in (None, Mock(value="invalid_gamemode"), *PlayerGamemode)
        for platform in (None, Mock(value="invalid_platform"), *PlayerPlatform)
    ],
    indirect=["player_html_data"],
)
def test_get_player_stats(
    player_html_data: str,
    gamemode: PlayerGamemode | None,
    platform: PlayerPlatform | None,
):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        query_params = "&".join(
            [
                (f"gamemode={gamemode.value}" if gamemode else ""),
                (f"platform={platform.value}" if platform else ""),
            ]
        )
        params = f"?{query_params}" if any(param for param in query_params) else ""
        response = client.get(f"/players/TeKrop-2217/stats/summary{params}")

    if (gamemode and gamemode not in gamemodes) or (
        platform and platform not in platforms
    ):
        assert response.status_code == 422
    else:
        assert response.status_code == 200

        filtered_data = read_json_file(
            f"players/stats/filtered/TeKrop-2217-{gamemode}-{platform}.json"
        )
        assert response.json() == filtered_data


@pytest.mark.parametrize(
    "player_html_data", [("Player-137712")], indirect=["player_html_data"]
)
def test_get_private_player_stats(
    player_html_data: str,
):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        response = client.get("/players/Player-137712/stats/summary")

    filtered_data = read_json_file("players/stats/filtered/Player-137712.json")

    assert response.status_code == 200
    assert response.json() == filtered_data


def test_get_player_stats_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}"
        )

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_stats_blizzard_timeout():
    with patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}"
        )

    assert response.status_code == 504
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        )
    }


def test_get_player_stats_internal_error():
    with patch(
        "overfastapi.handlers.get_player_stats_summary_request_handler.GetPlayerStatsSummaryRequestHandler.process_request",
        return_value={
            "general": [{"category": "invalid_value", "stats": [{"key": "test"}]}]
        },
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats/summary?gamemode={PlayerGamemode.QUICKPLAY}"
        )
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
