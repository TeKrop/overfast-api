from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.config import settings
from app.roles.enums import Role


@pytest.fixture(scope="module", autouse=True)
def _setup_heroes_test(heroes_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
    ):
        yield


def test_get_heroes(client: TestClient):
    response = client.get("/heroes")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


@pytest.mark.parametrize("role", [r.value for r in Role])
def test_get_heroes_filter_by_role(client: TestClient, role: Role):
    response = client.get(f"/heroes?role={role}")
    assert response.status_code == status.HTTP_200_OK
    assert all(hero["role"] == role for hero in response.json())


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
        "app.heroes.controllers.list_heroes_controller.ListHeroesController.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = client.get("/heroes")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


def test_get_heroes_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get("/heroes")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }
