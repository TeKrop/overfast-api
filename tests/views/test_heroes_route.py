from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.common.cache_manager import CacheManager
from app.common.enums import Locale, Role
from app.common.helpers import overfast_client
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _setup_heroes_test(heroes_html_data: str):
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        yield


def test_get_heroes(heroes_json_data: list):
    response = client.get("/heroes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == heroes_json_data


def test_get_heroes_when_no_cache(heroes_json_data: list):
    with patch("app.common.mixins.settings.use_api_cache_in_app", True):
        response = client.get("/heroes")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == heroes_json_data


def test_get_heroes_from_api_cache(heroes_json_data: list):
    with patch("app.common.mixins.settings.use_api_cache_in_app", True):
        cache_manager = CacheManager()
        cache_manager.update_api_cache("/heroes", heroes_json_data, 100)

        response = client.get("/heroes")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == heroes_json_data


def test_get_heroes_from_parser_cache(heroes_json_data: list):
    cache_manager = CacheManager()
    cache_manager.update_parser_cache(
        f"HeroesParser-{settings.blizzard_host}/{Locale.ENGLISH_US}{settings.heroes_path}",
        heroes_json_data,
        100,
    )

    response = client.get("/heroes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == heroes_json_data


@pytest.mark.parametrize(
    "role",
    [r.value for r in Role],
)
def test_get_heroes_filter_by_role(role: Role, heroes_json_data: list):
    response = client.get(f"/heroes?role={role}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        hero for hero in heroes_json_data if hero["role"] == role
    ]


def test_get_heroes_invalid_role():
    response = client.get("/heroes?role=invalid")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
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
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, text="Service Unavailable"
        ),
    ):
        response = client.get("/heroes")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_heroes_internal_error():
    with patch(
        "app.handlers.list_heroes_request_handler.ListHeroesRequestHandler.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/heroes")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
