from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.common.enums import HeroKeyCareerFilter, PlayerGamemode, PlayerPlatform
from app.common.helpers import overfast_client
from app.main import app

client = TestClient(app)
platforms = {p.value for p in PlayerPlatform}
gamemodes = {g.value for g in PlayerGamemode}
heroes = {h.value for h in HeroKeyCareerFilter}


@pytest.mark.parametrize(
    ("player_html_data", "player_json_data", "gamemode", "platform", "hero"),
    [
        ("TeKrop-2217", "TeKrop-2217", gamemode, platform, hero)
        for gamemode in (None, Mock(value="invalid_gamemode"), *PlayerGamemode)
        for platform in (None, Mock(value="invalid_platform"), *PlayerPlatform)
        for hero in (
            None,
            Mock(value="invalid_hero"),
            *[
                HeroKeyCareerFilter.ANA,
                HeroKeyCareerFilter.GENJI,
                HeroKeyCareerFilter.REINHARDT,
            ],
        )
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_stats(
    player_html_data: str,
    player_json_data: dict,
    gamemode: PlayerGamemode | None,
    platform: PlayerPlatform | None,
    hero: HeroKeyCareerFilter | None,
):
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=player_html_data),
    ):
        query_params = "&".join(
            [
                (f"gamemode={gamemode.value}" if gamemode else ""),
                (f"platform={platform.value}" if platform else ""),
                (f"hero={hero.value}" if hero else ""),
            ]
        )
        params = f"?{query_params}" if query_params else ""
        response = client.get(f"/players/TeKrop-2217/stats{params}")

    # Gamemode is a mandatory option
    if (
        gamemode not in gamemodes
        or (platform and platform not in platforms)
        or (hero and hero not in heroes)
    ):
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        assert response.status_code == status.HTTP_200_OK

        filtered_data = player_json_data["stats"] or {}

        if not platform:
            # Retrieve a "default" platform is the user didn't provided one
            possible_platforms = [
                platform_key
                for platform_key, platform_data in filtered_data.items()
                if platform_data is not None
            ]
            # If there is no data in any platform, just return nothing
            if not possible_platforms:
                assert response.json() == {}
                return
            # Take the first one of the list, usually there will be only one.
            # If there are two, the PC stats should come first
            platform = possible_platforms[0]

        filtered_data = ((filtered_data.get(platform) or {}).get(gamemode) or {}).get(
            "career_stats"
        ) or {}

        assert response.json() == {
            hero_key: statistics
            for hero_key, statistics in filtered_data.items()
            if not hero or hero == hero_key
        }


def test_get_player_stats_blizzard_error():
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, text="Service Unavailable"
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}"
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_stats_blizzard_timeout():
    with patch.object(
        overfast_client,
        "get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}"
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        )
    }


def test_get_player_stats_internal_error():
    with patch(
        "app.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",
        return_value={
            "ana": [{"category": "invalid_value", "stats": [{"key": "test"}]}]
        },
    ):
        response = client.get(
            f"/players/TeKrop-2217/stats?gamemode={PlayerGamemode.QUICKPLAY}"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
