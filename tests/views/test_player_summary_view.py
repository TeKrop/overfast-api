# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "player_id,platform,player_html_data,player_json_data",
    [
        ("Ka1zen_x", "psn", "Ka1zen_x", "Ka1zen_x"),
        ("mightyy_Brig", "psn", "mightyy_Brig", "mightyy_Brig"),
        (
            "test-e66c388f13a7f408a6e1738f3d5161e2",
            "nintendo-switch",
            "test-e66c388f13a7f408a6e1738f3d5161e2",
            "test-e66c388f13a7f408a6e1738f3d5161e2",
        ),
        ("xJaymog", "xbl", "xJaymog", "xJaymog"),
        ("TeKrop-2217", "pc", "TeKrop-2217", "TeKrop-2217"),
        ("Player-162460", "pc", "Player-162460", "Player-162460"),
        ("test-1337", "pc", "test-1337", "test-1337"),
        (
            "test-325d682072d7a4c61c33b6bbaa83b859",
            "nintendo-switch",
            "test-325d682072d7a4c61c33b6bbaa83b859",
            "test-325d682072d7a4c61c33b6bbaa83b859",
        ),
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_summary(
    player_id: str,
    platform: str,
    player_html_data: str,
    player_json_data: dict,
):
    with patch(
        "requests.get",
        side_effect=[
            Mock(
                status_code=200,
                text=player_html_data,
            ),
            Mock(
                status_code=200,
                json=lambda: [{"urlName": player_id}],
            ),
        ],
    ):
        response = client.get(f"/players/{platform}/{player_id}/summary")
    assert response.status_code == 200
    assert response.json() == player_json_data["summary"]


def test_get_player_summary_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/players/pc/TeKrop-2217/summary")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_summary_internal_error():
    with patch(
        "overfastapi.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",  # pylint: disable=C0301
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players/pc/TeKrop-2217/summary")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
