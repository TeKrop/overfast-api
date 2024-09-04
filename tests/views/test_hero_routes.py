from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.common.enums import HeroKey
from app.common.helpers import read_csv_data_file
from app.config import settings


@pytest.mark.parametrize(
    ("hero_name"),
    [(h.value) for h in (HeroKey.ANA, HeroKey.GENJI, HeroKey.REINHARDT)],
)
def test_get_hero(client: TestClient, hero_name: str):
    response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == status.HTTP_200_OK


def test_get_unreleased_hero(client: TestClient):
    response = client.get("/heroes/unknown-hero")
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
        assert response.json() == {"error": settings.internal_server_error_message}


def test_get_hero_no_portrait(client: TestClient, heroes_json_data: list[dict]):
    hero_name = HeroKey.ANA
    heroes_data = [
        hero_data for hero_data in heroes_json_data if hero_data["key"] != hero_name
    ]

    with patch(
        "app.parsers.heroes_parser.HeroesParser.filter_request_using_query",
        return_value=heroes_data,
    ):
        response = client.get(f"/heroes/{hero_name}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["portrait"] is None


def test_get_hero_no_hitpoints(client: TestClient):
    hero_name = HeroKey.ANA
    heroes_stats = [
        hero_stat
        for hero_stat in read_csv_data_file("heroes.csv")
        if hero_stat["key"] != hero_name
    ]

    with patch(
        "app.parsers.generics.csv_parser.read_csv_data_file",
        return_value=heroes_stats,
    ):
        response = client.get(f"/heroes/{hero_name}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["hitpoints"] is None
