import json
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import TimeoutException

from app.common.helpers import players_ids


@pytest.mark.parametrize(
    ("player_id", "player_html_data", "player_json_data"),
    [
        (player_id, player_id, player_id)
        for player_id in players_ids
        if player_id != "Unknown-1234"
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_career(
    client: TestClient,
    player_id: str,
    player_html_data: str,
    player_json_data: dict,
    search_tekrop_blizzard_json_data: dict,
    search_html_data: str,
):
    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                # Player HTML page
                Mock(status_code=status.HTTP_200_OK, text=player_html_data),
                # Search results related to the player (for namecard)
                Mock(
                    status_code=status.HTTP_200_OK,
                    text=json.dumps(search_tekrop_blizzard_json_data),
                    json=lambda: search_tekrop_blizzard_json_data,
                ),
                # Search results related to the player (for last_updated_at)
                Mock(
                    status_code=status.HTTP_200_OK,
                    text=json.dumps(search_tekrop_blizzard_json_data),
                    json=lambda: search_tekrop_blizzard_json_data,
                ),
            ],
        ),
        patch(
            "httpx.get",
            # Search HTML page for namecard retrieval
            return_value=Mock(status_code=status.HTTP_200_OK, text=search_html_data),
        ),
    ):
        response = client.get(f"/players/{player_id}")

    # Only assert the status and some elements from the response
    # We already check the entire content in parsers UT
    assert response.status_code == status.HTTP_200_OK

    response_json = response.json()
    assert response_json["summary"] == player_json_data["summary"]  # for namecard


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


def test_get_player_career_internal_error(client: TestClient):
    with patch(
        "app.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players/TeKrop-2217")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        }


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_get_player_parser_init_error(client: TestClient, player_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=player_html_data),
    ):
        response = client.get("/players/TeKrop-2217")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "Player not found"}


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_parser_parsing_error(client: TestClient, player_html_data: str):
    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"',
        'class="blabla"',
    )
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=player_attr_error),
    ):
        response = client.get("/players/TeKrop-2217")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        }
