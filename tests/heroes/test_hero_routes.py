from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.config import settings
from app.heroes.enums import HeroKey


@pytest.mark.parametrize(
    ("hero_name", "hero_html_data"),
    [(h.value, h.value) for h in HeroKey],
    indirect=["hero_html_data"],
)
def test_get_hero(
    client: TestClient,
    hero_name: str,
    hero_html_data: str,
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
    assert len(response.json()) > 0


@pytest.mark.parametrize(
    ("hero_html_data"),
    [("unknown-hero")],
    indirect=["hero_html_data"],
)
def test_get_unreleased_hero(client: TestClient, hero_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            Mock(status_code=status.HTTP_404_NOT_FOUND, text=hero_html_data),
        ],
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")
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
        "app.heroes.controllers.get_hero_controller.GetHeroController.process_request",
        return_value={"invalid_key": "invalid_value"},
    ):
        response = client.get(f"/heroes/{HeroKey.ANA}")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


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
):
    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                Mock(status_code=status.HTTP_200_OK, text=hero_html_data),
                Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
            ],
        ),
        patch(
            "app.heroes.parsers.heroes_parser.HeroesParser.filter_request_using_query",
            return_value=[],
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
    with (
        patch(
            "httpx.AsyncClient.get",
            side_effect=[
                Mock(status_code=status.HTTP_200_OK, text=hero_html_data),
                Mock(status_code=status.HTTP_200_OK, text=heroes_html_data),
            ],
        ),
        patch(
            "app.parsers.read_csv_data_file",
            return_value=[],
        ),
    ):
        response = client.get(f"/heroes/{hero_name}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["hitpoints"] is None


def test_get_hero_blizzard_forbidden_error_and_caching(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_403_FORBIDDEN, text="403 Forbidden"),
    ):
        response1 = client.get(f"/heroes/{HeroKey.ANA}")
    response2 = client.get(f"/heroes/{HeroKey.ANA}")

    assert (
        response1.status_code
        == response2.status_code
        == status.HTTP_429_TOO_MANY_REQUESTS
    )
    assert (
        response1.json()
        == response2.json()
        == {
            "error": (
                "API has been rate limited by Blizzard, please wait for "
                f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
            )
        }
    )
