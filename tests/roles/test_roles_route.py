from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from fastapi import status

from app.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_roles(client: TestClient, home_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=home_html_data),
    ):
        response = client.get("/roles")
    assert response.status_code == status.HTTP_200_OK


def test_get_roles_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            text="Service Unavailable",
        ),
    ):
        response = client.get("/roles")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 429 error) : Service Unavailable",
    }


def test_get_roles_internal_error(client: TestClient):
    with patch(
        "app.roles.controllers.list_roles_controller.ListRolesController.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/roles")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


def test_get_roles_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get("/roles")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }
