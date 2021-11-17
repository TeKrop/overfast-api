# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "player_id,platform,player_level,player_html_data,player_json_data",
    [
        ("Ka1zen_x", "psn", 1319, "Ka1zen_x", "Ka1zen_x"),
        ("mightyy_Brig", "psn", 111, "mightyy_Brig", "mightyy_Brig"),
        (
            "test-e66c388f13a7f408a6e1738f3d5161e2",
            "nintendo-switch",
            952,
            "test-e66c388f13a7f408a6e1738f3d5161e2",
            "test-e66c388f13a7f408a6e1738f3d5161e2",
        ),
        ("xJaymog", "xbl", 2534, "xJaymog", "xJaymog"),
        ("TeKrop-2217", "pc", 2415, "TeKrop-2217", "TeKrop-2217"),
        ("Player-162460", "pc", 194, "Player-162460", "Player-162460"),
        ("test-1337", "pc", 506, "test-1337", "test-1337"),
        (
            "test-325d682072d7a4c61c33b6bbaa83b859",
            "nintendo-switch",
            40,
            "test-325d682072d7a4c61c33b6bbaa83b859",
            "test-325d682072d7a4c61c33b6bbaa83b859",
        ),
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_get_player_career(
    player_id: str,
    platform: str,
    player_level: int,
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
                json=lambda: [{"urlName": player_id, "level": player_level}],
            ),
        ],
    ):
        response = client.get(f"/players/{platform}/{player_id}")
    assert response.status_code == 200
    assert response.json() == player_json_data


def test_get_player_career_blizzard_error():
    with patch(
        "requests.get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get("/players/pc/TeKrop-2217")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_player_career_internal_error():
    with patch(
        "overfastapi.handlers.get_player_career_request_handler.GetPlayerCareerRequestHandler.process_request",  # pylint: disable=C0301
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get("/players/pc/TeKrop-2217")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_get_player_parser_init_error(player_html_data: str):
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=player_html_data,
        ),
    ):
        response = client.get("/players/pc/TeKrop-2217")
        assert response.status_code == 404
        assert response.json() == {"error": "Player not found"}


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_get_player_parser_parsing_error(player_html_data: str):
    player_attr_error = player_html_data.replace(
        'class="masthead-player"', 'class="blabla"'
    )
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=player_attr_error,
        ),
    ):
        response = client.get("/players/pc/TeKrop-2217")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
