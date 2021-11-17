# pylint: disable=C0114,C0116
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from overfastapi.common.enums import HeroKey
from overfastapi.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "hero_name,hero_html_data,hero_json_data",
    [
        ("ana", "ana", "ana"),
        ("ashe", "ashe", "ashe"),
        ("baptiste", "baptiste", "baptiste"),
        ("bastion", "bastion", "bastion"),
        ("brigitte", "brigitte", "brigitte"),
        ("cassidy", "cassidy", "cassidy"),
        ("dva", "dva", "dva"),
        ("doomfist", "doomfist", "doomfist"),
        ("echo", "echo", "echo"),
        ("genji", "genji", "genji"),
        ("hanzo", "hanzo", "hanzo"),
        ("junkrat", "junkrat", "junkrat"),
        ("lucio", "lucio", "lucio"),
        ("mei", "mei", "mei"),
        ("mercy", "mercy", "mercy"),
        ("moira", "moira", "moira"),
        ("orisa", "orisa", "orisa"),
        ("pharah", "pharah", "pharah"),
        ("reaper", "reaper", "reaper"),
        ("reinhardt", "reinhardt", "reinhardt"),
        ("roadhog", "roadhog", "roadhog"),
        ("sigma", "sigma", "sigma"),
        ("soldier-76", "soldier-76", "soldier-76"),
        ("sombra", "sombra", "sombra"),
        ("symmetra", "symmetra", "symmetra"),
        ("torbjorn", "torbjorn", "torbjorn"),
        ("tracer", "tracer", "tracer"),
        ("widowmaker", "widowmaker", "widowmaker"),
        ("winston", "winston", "winston"),
        ("wrecking-ball", "wrecking-ball", "wrecking-ball"),
        ("zarya", "zarya", "zarya"),
        ("zenyatta", "zenyatta", "zenyatta"),
    ],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_get_hero(hero_name: str, hero_html_data: str, hero_json_data: dict):
    with patch(
        "requests.get",
        return_value=Mock(
            status_code=200,
            text=hero_html_data,
        ),
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == 200
    assert response.json() == hero_json_data


def test_get_hero_blizzard_error():
    with patch(
        "requests.get",
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
