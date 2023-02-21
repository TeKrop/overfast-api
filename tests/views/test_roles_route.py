from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.helpers import overfast_client
from overfastapi.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_roles_test(home_html_data: str):
    with patch.object(
        overfast_client, "get", return_value=Mock(status_code=200, text=home_html_data)
    ):
        yield


def test_get_roles(roles_json_data: list):
    response = client.get("/roles")
    assert response.status_code == 200
    assert response.json() == roles_json_data


def test_get_roles_after_get_gamemodes(roles_json_data: list):
    # Used to check we don't have any conflict between parsers
    # using the same Blizzard URL and associated Parser caches
    client.get("/gamemodes")
    response = client.get("/roles")
    assert response.status_code == 200
    assert response.json() == roles_json_data


def test_get_roles_blizzard_error():
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/roles")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_roles_internal_error():
    with patch(
        "overfastapi.handlers.list_roles_request_handler.ListRolesRequestHandler.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/roles")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
