# pylint: disable=C0114,C0116
import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import PlayerPlatform, PlayerPrivacy
from overfastapi.main import app

client = TestClient(app)
platforms = {p.value for p in PlayerPlatform}
privacies = {p.value for p in PlayerPrivacy}


@pytest.fixture(scope="module", autouse=True)
def setup_search_players_test(search_players_blizzard_json_data: list[dict]):
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=json.dumps(search_players_blizzard_json_data),
            json=lambda: search_players_blizzard_json_data,
        ),
    ):
        yield


def test_search_players_missing_name():
    response = client.get("/players?platform=pc")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["query", "name"],
                "msg": "field required",
                "type": "value_error.missing",
            }
        ]
    }


def test_search_players_no_result():
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text="[]",
            json=lambda: [],
        ),
    ):
        response = client.get("/players?name=Player")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "results": []}


def test_search_players_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/players?name=Player")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_search_players(search_players_api_json_data: dict):
    response = client.get("/players?name=Test")
    assert response.status_code == 200
    assert response.json() == {
        "total": search_players_api_json_data["total"],
        "results": search_players_api_json_data["results"][0:20],
    }


def test_search_players_with_cache(search_players_api_json_data: list):
    with patch("overfastapi.common.mixins.USE_API_CACHE_IN_APP", True):
        players_response_data = {
            "total": search_players_api_json_data["total"],
            "results": search_players_api_json_data["results"][0:20],
        }

        cache_manager = CacheManager()
        cache_manager.update_api_cache(
            "/players?name=Test", json.dumps(players_response_data), 100
        )

        response = client.get("/players?name=Test")
        assert response.status_code == 200
        assert response.json() == players_response_data


@pytest.mark.parametrize(
    "platform",
    [*[p.value for p in PlayerPlatform], "invalid_platform", 1234],
)
def test_search_players_filter_by_platform(
    platform: PlayerPlatform, search_players_api_json_data: dict
):
    response = client.get(f"/players?name=Test&platform={platform}")

    if platform in platforms:
        filtered_players = [
            player
            for player in search_players_api_json_data["results"]
            if player["platform"] == platform
        ]
        assert response.status_code == 200
        assert response.json() == {
            "total": len(filtered_players),
            "results": filtered_players[0:20],
        }
    else:
        assert response.status_code == 422


@pytest.mark.parametrize(
    "privacy",
    [*[p.value for p in PlayerPrivacy], "invalid_privacy", 1234],
)
def test_search_players_filter_by_privacy(
    privacy: PlayerPrivacy, search_players_api_json_data: dict
):
    response = client.get(f"/players?name=Test&privacy={privacy}")

    if privacy in privacies:
        filtered_players = [
            player
            for player in search_players_api_json_data["results"]
            if player["privacy"] == privacy
        ]
        assert response.status_code == 200
        assert response.json() == {
            "total": len(filtered_players),
            "results": filtered_players[0:20],
        }
    else:
        assert response.status_code == 422


@pytest.mark.parametrize(
    "level",
    [1, 20, 40, 60, 150, -10, 0, "invalid_level"],
)
def test_search_players_filter_by_min_level(
    level: int, search_players_api_json_data: dict
):
    response = client.get(f"/players?name=Test&min_level={level}")

    if isinstance(level, int) and level > 0:
        filtered_players = [
            player
            for player in search_players_api_json_data["results"]
            if player["level"] >= level
        ]
        assert response.status_code == 200
        assert response.json() == {
            "total": len(filtered_players),
            "results": filtered_players[0:20],
        }
    else:
        assert response.status_code == 422


@pytest.mark.parametrize(
    "level",
    [1, 20, 40, 60, 150, -10, 0, "invalid_level"],
)
def test_search_players_filter_by_max_level(
    level: int, search_players_api_json_data: dict
):
    response = client.get(f"/players?name=Test&max_level={level}")

    if isinstance(level, int) and level > 0:
        filtered_players = [
            player
            for player in search_players_api_json_data["results"]
            if player["level"] <= level
        ]
        assert response.status_code == 200
        assert response.json() == {
            "total": len(filtered_players),
            "results": filtered_players[0:20],
        }
    else:
        assert response.status_code == 422


def test_search_players_filter_multiple(search_players_api_json_data: dict):
    response = client.get(
        "/players?name=Test&min_level=20&max_level=40&platform=pc&privacy=public"
    )

    filtered_players = [
        player
        for player in search_players_api_json_data["results"]
        if (
            player["level"] >= 20
            and player["level"] <= 40
            and player["platform"] == "pc"
            and player["privacy"] == "public"
        )
    ]
    assert response.status_code == 200
    assert response.json() == {
        "total": len(filtered_players),
        "results": filtered_players[0:20],
    }


def test_search_players_ordering_asc(search_players_api_json_data: dict):
    response = client.get("/players?name=Test&order_by=name:asc")

    search_players_api_json_data["results"].sort(
        key=lambda player: player["name"], reverse=False
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": search_players_api_json_data["total"],
        "results": search_players_api_json_data["results"][0:20],
    }


def test_search_players_ordering_desc(search_players_api_json_data: dict):
    response = client.get("/players?name=Test&order_by=level:desc")

    search_players_api_json_data["results"].sort(
        key=lambda player: player["level"], reverse=True
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": search_players_api_json_data["total"],
        "results": search_players_api_json_data["results"][0:20],
    }


def test_search_players_internal_error():
    with patch(
        "overfastapi.handlers.search_players_request_handler.SearchPlayersRequestHandler.process_request",  # pylint: disable=C0301
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players?name=Test")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
