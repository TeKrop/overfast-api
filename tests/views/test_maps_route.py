# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.enums import MapGamemode
from overfastapi.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_maps_test(maps_html_data: str):
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=maps_html_data,
        ),
    ):
        yield


def test_get_maps(maps_json_data: list):
    response = client.get("/maps")
    assert response.status_code == 200
    assert response.json() == maps_json_data


@pytest.mark.parametrize(
    "gamemode",
    [g.value for g in MapGamemode],
)
def test_get_maps_filter_by_gamemode(gamemode: MapGamemode, maps_json_data: list):
    response = client.get(f"/maps?gamemode={gamemode}")
    assert response.status_code == 200
    assert response.json() == [
        ow_map for ow_map in maps_json_data if gamemode in ow_map["gamemodes"]
    ]


def test_get_maps_invalid_gamemode():
    response = client.get("/maps?gamemode=invalid")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["query", "gamemode"],
                "msg": (
                    "value is not a valid enumeration member; permitted: 'assault', "
                    "'control', 'ctf', 'deathmatch', 'elimination', 'escort', 'hybrid', "
                    "'team-deathmatch'"
                ),
                "type": "type_error.enum",
                "ctx": {
                    "enum_values": [
                        "assault",
                        "control",
                        "ctf",
                        "deathmatch",
                        "elimination",
                        "escort",
                        "hybrid",
                        "team-deathmatch",
                    ]
                },
            }
        ]
    }


def test_get_maps_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/maps")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_maps_internal_error():
    with patch(
        "overfastapi.handlers.list_maps_request_handler.ListMapsRequestHandler.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/maps")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
