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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get("/roles")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_roles_internal_error(client: TestClient):
    with patch(
        "app.domain.services.role_service.RoleService.list_roles",
        return_value=([{"invalid_key": "invalid_value"}], False, 0),
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

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": (
            "Blizzard is temporarily rate limiting this API. Please retry after 60 seconds."
        )
    }
