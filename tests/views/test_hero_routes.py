from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.enums import HeroKey
from overfastapi.common.helpers import overfast_client
from overfastapi.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "hero_name,hero_html_data,hero_json_data",
    [
        (h.value, h.value, h.value)
        for h in [HeroKey.ANA, HeroKey.GENJI, HeroKey.REINHARDT]
    ],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_get_hero(
    hero_name: str, hero_html_data: str, hero_json_data: dict, heroes_html_data: str
):
    with patch.object(
        overfast_client,
        "get",
        side_effect=[
            Mock(status_code=200, text=hero_html_data),
            Mock(status_code=200, text=heroes_html_data),
        ],
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == 200
    assert response.json() == hero_json_data


def test_get_hero_blizzard_error():
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=503, text="Service Unavailable"),
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")

    assert response.status_code == 504
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"
    }


def test_get_hero_internal_error():
    with patch(
        "overfastapi.handlers.get_hero_request_handler.GetHeroRequestHandler.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")
        assert response.status_code == 500
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            )
        }
