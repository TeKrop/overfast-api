from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.config import settings
from app.players.enums import PlayerGamemode, PlayerPlatform, PlayerRegion

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def _setup_hero_stats_test(hero_stats_response_mock: Mock):
    with patch("httpx.AsyncClient.get", return_value=hero_stats_response_mock):
        yield


def test_get_hero_stats_missing_parameters(client: TestClient):
    response = client.get("/heroes/stats")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_success(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={
            "platform": PlayerPlatform.PC,
            "gamemode": PlayerGamemode.QUICKPLAY,
            "region": PlayerRegion.EUROPE,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_hero_stats_invalid_platform(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={
            "platform": "invalid_platform",
            "gamemode": PlayerGamemode.QUICKPLAY,
            "region": PlayerRegion.EUROPE,
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_invalid_gamemode(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={
            "platform": PlayerPlatform.PC,
            "gamemode": "invalid_gamemode",
            "region": PlayerRegion.EUROPE,
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_invalid_region(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={
            "platform": PlayerPlatform.PC,
            "gamemode": PlayerGamemode.QUICKPLAY,
            "region": "invalid_region",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get(
            "/heroes/stats",
            params={
                "platform": PlayerPlatform.PC,
                "gamemode": PlayerGamemode.QUICKPLAY,
                "region": PlayerRegion.EUROPE,
            },
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_heroes_internal_error(client: TestClient):
    with patch(
        "app.domain.services.hero_service.HeroService.get_hero_stats",
        return_value=([{"invalid_key": "invalid_value"}], False),
    ):
        response = client.get(
            "/heroes/stats",
            params={
                "platform": PlayerPlatform.PC,
                "gamemode": PlayerGamemode.QUICKPLAY,
                "region": PlayerRegion.EUROPE,
            },
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}


def test_get_heroes_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get(
            "/heroes/stats",
            params={
                "platform": PlayerPlatform.PC,
                "gamemode": PlayerGamemode.QUICKPLAY,
                "region": PlayerRegion.EUROPE,
            },
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }
