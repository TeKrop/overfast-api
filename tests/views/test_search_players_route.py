from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException


def test_search_players(client: TestClient):
    response = client.get("/players?name=Test")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["results"]) > 0


@pytest.mark.parametrize(
    ("offset", "limit"),
    [(0, 10), (10, 20), (0, 100), (100, 20)],
)
def test_search_players_with_offset_and_limit(
    client: TestClient, offset: int, limit: int
):
    response = client.get(f"/players?name=Test&offset={offset}&limit={limit}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["results"]) <= limit


@pytest.mark.parametrize("order_by", ["name:asc", "name:desc"])
def test_search_players_ordering(client: TestClient, order_by: str):
    response = client.get(f"/players?name=Test&order_by={order_by}")

    order_field, order_arrangement = order_by.split(":")
    assert response.status_code == status.HTTP_200_OK
    sorted_results = sorted(
        response.json()["results"],
        key=lambda player: player[order_field],
        reverse=order_arrangement == "desc",
    )
    assert sorted_results == response.json()["results"]


def test_search_players_missing_name(client: TestClient):
    response = client.get("/players")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_search_players_no_result(client: TestClient):
    response = client.get("/players?name=zyxfffffffff")
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
        response = client.get("/players?name=Player")

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
        response = client.get("/players?name=Player")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


def test_search_players_internal_error(client: TestClient):
    with patch(
        "app.handlers.search_players_request_handler.SearchPlayersRequestHandler.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players?name=Test")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        }
