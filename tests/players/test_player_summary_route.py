from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.config import settings
from tests.helpers import players_ids


@pytest.mark.parametrize(
    ("player_id", "player_html_data"),
    [(player_id, player_id) for player_id in players_ids],
    indirect=["player_html_data"],
)
def test_get_player_summary(
    client: TestClient,
    player_id: str,
    player_html_data: str,
    player_search_response_mock: Mock,
    blizzard_unlock_response_mock: Mock,
):
    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Players search call first
                player_search_response_mock,
                # Player profile page
                Mock(status_code=status.HTTP_200_OK, text=player_html_data),
            ],
        ),
        # UnlocksManager call
        patch("httpx.get", return_value=blizzard_unlock_response_mock),
    ):
        response = client.get(f"/players/{player_id}/summary")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


def test_get_player_summary_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get("/players/TeKrop-2217/summary")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_player_summary_blizzard_timeout(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get("/players/TeKrop-2217/summary")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


def test_get_player_summary_internal_error(client: TestClient):
    with patch(
        "app.players.controllers.get_player_career_controller.GetPlayerCareerController.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players/TeKrop-2217/summary")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


def test_get_player_summary_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get("/players/TeKrop-2217/summary")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }
