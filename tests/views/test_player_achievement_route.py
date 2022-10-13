# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.enums import PlayerAchievementCategory
from overfastapi.main import app

client = TestClient(app)
achievement_categories = {c.value for c in PlayerAchievementCategory}


@pytest.mark.parametrize(
    "player_html_data,player_json_data,category",
    [
        ("TeKrop-2217", "TeKrop-2217", category)
        for category in (
            None,
            Mock(value="invalid_category"),
            *PlayerAchievementCategory,
        )
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_achievements(
    player_html_data: str,
    player_json_data: dict,
    category: PlayerAchievementCategory | None,
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
        response = client.get(
            "/players/pc/TeKrop-2217/achievements"
            + (f"?category={category.value}" if category else "")
        )

    # Gamemode is a mandatory option
    if category and category not in achievement_categories:
        assert response.status_code == 422
    else:
        assert response.status_code == 200
        assert response.json() == {
            category_key: achievements
            for category_key, achievements in (
                (player_json_data.get("achievements") or {}).items()
            )
            if not category or category == category_key
        }


def test_get_player_achievements_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/players/pc/TeKrop-2217/achievements")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_achievements_internal_error():
    with patch(
        "overfastapi.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",  # pylint: disable=C0301
        return_value={"general": [{"title": "invalid_title"}]},
    ):
        response = client.get("/players/pc/TeKrop-2217/achievements")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
