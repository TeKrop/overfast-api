import json
from unittest.mock import Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import PlayerPrivacy
from overfastapi.main import app

client = TestClient(app)
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
    response = client.get("/players?privacy=public")
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
        return_value=Mock(status_code=200, text="[]", json=lambda: []),
    ):
        response = client.get("/players?name=Player")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "results": []}


@pytest.mark.parametrize(
    "status_code,text",
    [
        (503, "Service Unavailable"),
        (500, '{"error":"searchByName error"}'),
    ],
)
def test_search_players_blizzard_error(status_code: int, text: str):
    with patch(
        "requests.get",
        return_value=Mock(status_code=status_code, text=text),
    ):
        response = client.get("/players?name=Player")

    assert response.status_code == 504
    assert response.json() == {
        "error": f"Couldn't get Blizzard page (HTTP {status_code} error) : {text}"
    }


def test_search_players_blizzard_timeout():
    with patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ):
        response = client.get("/players?name=Player")

    assert response.status_code == 504
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        )
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
    "offset,limit",
    [
        (0, 10),
        (10, 20),
        (0, 100),
        (100, 20),
    ],
)
def test_search_players_with_offset_and_limit(
    search_players_api_json_data: dict, offset: int, limit: int
):
    response = client.get(f"/players?name=Test&offset={offset}&limit={limit}")
    assert response.status_code == 200
    assert response.json() == {
        "total": search_players_api_json_data["total"],
        "results": search_players_api_json_data["results"][offset:limit],
    }


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


@pytest.mark.parametrize("order_by", ["name:asc", "name:desc"])
def test_search_players_ordering(search_players_api_json_data: dict, order_by: str):
    response = client.get(f"/players?name=Test&order_by={order_by}")

    order_field, order_arrangement = order_by.split(":")
    search_players_api_json_data["results"].sort(
        key=lambda player: player[order_field], reverse=order_arrangement == "desc"
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": search_players_api_json_data["total"],
        "results": search_players_api_json_data["results"][0:20],
    }


def test_search_players_internal_error():
    with patch(
        "overfastapi.handlers.search_players_request_handler.SearchPlayersRequestHandler.process_request",
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
