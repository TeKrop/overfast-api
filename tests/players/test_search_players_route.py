from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import TimeoutException

from app.config import settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _setup_search_players_test(player_search_response_mock: Mock):
    with patch(
        "httpx.AsyncClient.get",
        return_value=player_search_response_mock,
    ):
        yield


def test_search_players_missing_name(client: TestClient):
    response = client.get("/players")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_search_players_no_result(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text="[]", json=list),
    ):
        response = client.get("/players", params={"name": "Player"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"total": 0, "results": []}


@pytest.mark.parametrize(
    ("status_code", "text"),
    [
        (status.HTTP_503_SERVICE_UNAVAILABLE, "Service Unavailable"),
        (status.HTTP_500_INTERNAL_SERVER_ERROR, '{"error":"searchByName error"}'),
    ],
)
def test_search_players_blizzard_error(client: TestClient, status_code: int, text: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status_code, text=text),
    ):
        response = client.get("/players", params={"name": "Player"})

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": f"Couldn't get Blizzard page (HTTP {status_code} error) : {text}",
    }


def test_search_players_blizzard_timeout(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get("/players", params={"name": "Player"})

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


def test_get_roles_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get("/players", params={"name": "Player"})

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }


def test_search_players(client: TestClient):
    response = client.get("/players", params={"name": "Test"})
    assert response.status_code == status.HTTP_200_OK

    json_response = response.json()
    assert (
        json_response["results"]
        == sorted(json_response["results"], key=lambda k: k["player_id"])[:20]
    )


@pytest.mark.parametrize(
    ("offset", "limit"),
    [
        (0, 10),
        (10, 20),
        (0, 100),
        (100, 20),
    ],
)
def test_search_players_with_offset_and_limit(
    client: TestClient,
    offset: int,
    limit: int,
):
    response = client.get(
        "/players",
        params={
            "name": "Test",
            "offset": offset,
            "limit": limit,
        },
    )
    assert response.status_code == status.HTTP_200_OK

    json_response = response.json()
    assert (
        json_response["results"]
        == sorted(json_response["results"], key=lambda k: k["player_id"])[:limit]
    )


@pytest.mark.parametrize("order_by", ["name:asc", "name:desc"])
def test_search_players_ordering(
    client: TestClient,
    order_by: str,
):
    response = client.get(
        "/players",
        params={
            "name": "Test",
            "order_by": order_by,
        },
    )
    assert response.status_code == status.HTTP_200_OK

    order_field, order_arrangement = order_by.split(":")
    json_response = response.json()
    assert json_response["results"] == sorted(
        json_response["results"],
        key=lambda k: k[order_field],
        reverse=order_arrangement == "desc",
    )


def test_search_players_internal_error(client: TestClient):
    with patch(
        "app.players.controllers.search_players_controller.SearchPlayersController.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players", params={"name": "Test"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}
