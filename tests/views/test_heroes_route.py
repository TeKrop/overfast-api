from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.common.enums import Role


def test_get_heroes(client: TestClient):
    response = client.get("/heroes")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


@pytest.mark.parametrize("role", [r.value for r in Role])
def test_get_heroes_filter_by_role(client: TestClient, role: Role):
    response = client.get(f"/heroes?role={role}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_heroes_invalid_role(client: TestClient):
    response = client.get("/heroes?role=invalid")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_heroes_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get("/heroes")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_heroes_internal_error(client: TestClient):
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
            ),
        }
