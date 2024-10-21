from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.common.enums import HeroKey
from app.common.helpers import read_csv_data_file
from app.config import settings


@pytest.mark.parametrize(
    ("hero_name", "hero_html_data", "hero_json_data"),
    [
        (h.value, h.value, h.value)
        for h in (HeroKey.ANA, HeroKey.GENJI, HeroKey.REINHARDT)
    ],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_get_hero(
    client: TestClient,
    hero_name: str,
    hero_html_data: str,
    hero_json_data: dict,
    heroes_html_data: str,
):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            Mock(status_code=status.HTTP_200_OK, text=hero_html_data),
            Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
        ],
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == status.HTTP_200_OK

    response_json = response.json()
    del response_json["hitpoints"]

    hero_data = hero_json_data.copy()
    del hero_data["hitpoints"]

    assert response_json == hero_data


@pytest.mark.parametrize(
    ("hero_name", "hero_html_data"),
    [("lifeweaver", "unknown-hero")],
    indirect=["hero_html_data"],
)
def test_get_unreleased_hero(client: TestClient, hero_name: str, hero_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            Mock(status_code=status.HTTP_404_NOT_FOUND, text=hero_html_data),
        ],
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"error": "Hero not found or not released yet"}


def test_get_hero_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_hero_internal_error(client: TestClient):
    with patch(
        "app.handlers.get_hero_request_handler.GetHeroRequestHandler.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {
            "error": (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        }


def test_get_hero_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }


@pytest.mark.parametrize(
    ("hero_name", "hero_html_data"),
    [(HeroKey.ANA, HeroKey.ANA)],
    indirect=["hero_html_data"],
)
def test_get_hero_no_portrait(
    client: TestClient,
    hero_name: str,
    hero_html_data: str,
    heroes_html_data: str,
    heroes_json_data: list[dict],
):
    heroes_data = [
        hero_data for hero_data in heroes_json_data if hero_data["key"] != HeroKey.ANA
    ]

    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                Mock(status_code=status.HTTP_200_OK, text=hero_html_data),
                Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
            ],
        ),
        patch(
            "app.parsers.heroes_parser.HeroesParser.filter_request_using_query",
            return_value=heroes_data,
        ),
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["portrait"] is None


@pytest.mark.parametrize(
    ("hero_name", "hero_html_data"),
    [(HeroKey.ANA, HeroKey.ANA)],
    indirect=["hero_html_data"],
)
def test_get_hero_no_hitpoints(
    client: TestClient,
    hero_name: str,
    hero_html_data: str,
    heroes_html_data: str,
):
    heroes_stats = [
        hero_stat
        for hero_stat in read_csv_data_file("heroes.csv")
        if hero_stat["key"] != HeroKey.ANA
    ]

    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                Mock(status_code=status.HTTP_200_OK, text=hero_html_data),
                Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
            ],
        ),
        patch(
            "app.parsers.generics.csv_parser.read_csv_data_file",
            return_value=heroes_stats,
        ),
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["hitpoints"] is None
