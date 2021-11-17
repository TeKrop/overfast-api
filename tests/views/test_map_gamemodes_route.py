# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_map_gamemodes_test(maps_html_data):
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=maps_html_data,
        ),
    ):
        yield


def test_get_map_gamemodes(map_gamemodes_json_data: list):
    response = client.get("/maps/gamemodes")
    assert response.status_code == 200
    assert response.json() == map_gamemodes_json_data


def test_get_map_gamemodes_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/maps/gamemodes")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_map_gamemodes_internal_error():
    with patch(
        "overfastapi.handlers.list_map_gamemodes_request_handler.ListMapGamemodesRequestHandler.process_request",  # pylint: disable=C0301
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/maps/gamemodes")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
