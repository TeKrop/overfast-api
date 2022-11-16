from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.enums import HeroKey, PlayerGamemode
from overfastapi.main import app

client = TestClient(app)
gamemodes = {g.value for g in PlayerGamemode}
heroes = {h.value for h in HeroKey}


@pytest.mark.parametrize(
    "player_html_data,player_json_data,gamemode,hero",
    [
        ("TeKrop-2217", "TeKrop-2217", gamemode, hero)
        for gamemode in (None, Mock(value="invalid_gamemode"), *PlayerGamemode)
        for hero in (None, Mock(value="invalid_hero"), *HeroKey)
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_stats(
    player_html_data: str,
    player_json_data: dict,
    gamemode: PlayerGamemode | None,
    hero: HeroKey | None,
):
    with patch(
        "requests.get",
        side_effect=[
            Mock(
                status_code=200,
                text=player_html_data,
            ),
            Mock(
                status_code=200,
                json=lambda: [{"urlName": "TeKrop-2217"}],
            ),
        ],
    ):
        query_params = "&".join(
            [
                (f"gamemode={gamemode.value}" if gamemode else ""),
                (f"hero={hero.value}" if hero else ""),
            ]
        )
        response = client.get(
            "/players/pc/TeKrop-2217/stats"
            + (f"?{query_params}" if query_params else "")
        )

    # Gamemode is a mandatory option
    if gamemode not in gamemodes or (hero and hero not in heroes):
        assert response.status_code == 422
    else:
        assert response.status_code == 200
        assert response.json() == {
            hero_key: statistics
            for hero_key, statistics in (
                (
                    (player_json_data.get(gamemode) or {}).get("career_stats") or {}
                ).items()
            )
            if not hero or hero == hero_key
        }


def test_get_player_stats_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get(
            f"/players/pc/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}"
        )

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_stats_internal_error():
    with patch(
        "overfastapi.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",
        return_value={
            "ana": [{"category": "invalid_value", "stats": [{"key": "test"}]}]
        },
    ):
        response = client.get(
            f"/players/pc/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}"
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
