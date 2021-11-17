# pylint: disable=C0114,C0116
import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import Role
from overfastapi.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_heroes_test(heroes_html_data):
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=heroes_html_data,
        ),
    ):
        yield


def test_get_heroes(heroes_json_data: list):
    response = client.get("/heroes")
    assert response.status_code == 200
    assert response.json() == heroes_json_data


def test_get_heroes_when_no_cache(heroes_json_data: list):
    with patch("overfastapi.common.mixins.USE_API_CACHE_IN_APP", True):
        response = client.get("/heroes")
        assert response.status_code == 200
        assert response.json() == heroes_json_data


def test_get_heroes_from_api_cache(heroes_json_data: list):
    with patch("overfastapi.common.mixins.USE_API_CACHE_IN_APP", True):
        cache_manager = CacheManager()
        cache_manager.update_api_cache("/heroes", json.dumps(heroes_json_data), 100)

        response = client.get("/heroes")
        assert response.status_code == 200
        assert response.json() == heroes_json_data


def test_get_heroes_from_parser_cache(heroes_json_data: list):
    cache_manager = CacheManager()
    cache_manager.update_parser_cache(
        "/heroes",
        {
            "hash": "5c5dbe354c50edd1c90422005a546c7c",
            "data": json.dumps(heroes_json_data),
        },
    )

    response = client.get("/heroes")
    assert response.status_code == 200
    assert response.json() == heroes_json_data


@pytest.mark.parametrize(
    "role",
    [r.value for r in Role],
)
def test_get_heroes_filter_by_role(role: Role, heroes_json_data: list):
    response = client.get(f"/heroes?role={role}")
    assert response.status_code == 200
    assert response.json() == [
        hero for hero in heroes_json_data if hero["role"] == role
    ]


def test_get_heroes_invalid_role():
    response = client.get("/heroes?role=invalid")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["query", "role"],
                "msg": (
                    "value is not a valid enumeration member; "
                    "permitted: 'damage', 'support', 'tank'"
                ),
                "type": "type_error.enum",
                "ctx": {"enum_values": ["damage", "support", "tank"]},
            }
        ]
    }


def test_get_heroes_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/heroes")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_heroes_internal_error():
    with patch(
        "overfastapi.handlers.list_heroes_request_handler.ListHeroesRequestHandler.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/heroes")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
