from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import RemoteProtocolError, TimeoutException

from app.config import settings
from tests.helpers import players_ids

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("player_id", "player_html_data"),
    [(player_id, player_id) for player_id in players_ids],
    indirect=["player_html_data"],
)
def test_get_player_career(
    client: TestClient,
    player_id: str,
    player_html_data: str | None,
    player_search_response_mock: Mock,
):
    assert player_html_data is not None

    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        response = client.get(f"/players/{player_id}")

    # Only assert the status and some elements from the response
    # We already check the entire content in parsers UT
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


def test_get_player_career_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get("/players/TeKrop-2217")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_player_career_blizzard_timeout(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get("/players/TeKrop-2217")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : Blizzard took more "
            "than 10 seconds to respond, resulting in a timeout"
        ),
    }


def test_get_player_career_blizzard_remote_protocol_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=RemoteProtocolError(
            "<ConnectionTerminated error_code:0, last_stream_id:12101, additional_data:None>"
        ),
    ):
        response = client.get("/players/TeKrop-2217")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : Blizzard closed the "
            "connection, no data could be retrieved"
        ),
    }


def test_get_player_career_internal_error(client: TestClient):
    with patch(
        "app.players.controllers.get_player_career_controller.GetPlayerCareerController.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players/TeKrop-2217")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


def test_get_player_career_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get("/players/TeKrop-2217")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "error": (
            "Blizzard is currently rate limiting requests. "
            "Your request has been queued and will be retried automatically. "
            "Please try again in a moment."
        )
    }


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_get_player_parser_init_error(client: TestClient, player_html_data: str | None):
    assert player_html_data is not None

    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            Mock(status_code=status.HTTP_200_OK, text="[]", json=list),
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        response = client.get("/players/Unknown-1234")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "Player not found"}


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_parser_parsing_error(
    client: TestClient, player_html_data: str | None, player_search_response_mock: Mock
):
    assert player_html_data is not None

    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"',
        'class="blabla"',
    )
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_attr_error),
        ],
    ):
        response = client.get("/players/TeKrop-2217")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}
