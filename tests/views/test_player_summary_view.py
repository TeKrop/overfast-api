from unittest.mock import Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from overfastapi.common.helpers import players_ids
from overfastapi.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "player_id,player_html_data,player_json_data",
    [
        (player_id, player_id, player_id)
        for player_id in players_ids
        if player_id != "Unknown-1234"
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_summary(
    player_id: str,
    player_html_data: str,
    player_json_data: dict,
):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        response = client.get(f"/players/{player_id}/summary")
    assert response.status_code == 200
    assert response.json() == player_json_data["summary"]


def test_get_player_summary_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/players/TeKrop-2217/summary")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_summary_blizzard_timeout():
    with patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ):
        response = client.get("/players/TeKrop-2217/summary")

    assert response.status_code == 504
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        )
    }


def test_get_player_summary_internal_error():
    with patch(
        "overfastapi.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players/TeKrop-2217/summary")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
