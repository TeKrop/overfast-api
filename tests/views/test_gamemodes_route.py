from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.common.helpers import overfast_client
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _setup_gamemodes_test(home_html_data: str):
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=home_html_data),
    ):
        yield


def test_get_gamemodes(gamemodes_json_data: list):
    response = client.get("/gamemodes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == gamemodes_json_data


def test_get_gamemodes_internal_error():
    with patch(
        "app.handlers.list_gamemodes_request_handler."
        "ListGamemodesRequestHandler.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/gamemodes")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        }
