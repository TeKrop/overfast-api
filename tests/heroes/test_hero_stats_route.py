from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.config import settings
from app.domain.enums import (
    CompetitiveDivisionFilter,
    PlayerGamemode,
    PlayerPlatform,
    PlayerRegion,
    Role,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_BASE_PARAMS = {
    "platform": PlayerPlatform.PC,
    "gamemode": PlayerGamemode.QUICKPLAY,
    "region": PlayerRegion.EUROPE,
}

_COMPETITIVE_PARAMS = {
    "platform": PlayerPlatform.PC,
    "gamemode": PlayerGamemode.COMPETITIVE,
    "region": PlayerRegion.EUROPE,
}


@pytest.fixture(scope="module", autouse=True)
def _setup_hero_stats_test(hero_stats_response_mock: Mock):
    with patch("httpx.AsyncClient.get", return_value=hero_stats_response_mock):
        yield


def test_get_hero_stats_missing_parameters(client: TestClient):
    response = client.get("/heroes/stats")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_success(client: TestClient):
    response = client.get("/heroes/stats", params=_BASE_PARAMS)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_hero_stats_response_shape(client: TestClient):
    response = client.get("/heroes/stats", params=_BASE_PARAMS)

    first = response.json()[0]

    assert set(first.keys()) == {"hero", "pickrate", "winrate"}
    assert isinstance(first["hero"], str)
    assert isinstance(first["pickrate"], float)
    assert isinstance(first["winrate"], float)


def test_get_hero_stats_invalid_platform(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={**_BASE_PARAMS, "platform": "invalid_platform"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_invalid_gamemode(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={**_BASE_PARAMS, "gamemode": "invalid_gamemode"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_invalid_region(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={**_BASE_PARAMS, "region": "invalid_region"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("role", [r.value for r in Role])
def test_get_hero_stats_filter_by_role(client: TestClient, role: str):
    response = client.get("/heroes/stats", params={**_BASE_PARAMS, "role": role})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_hero_stats_filter_by_invalid_role(client: TestClient):
    response = client.get("/heroes/stats", params={**_BASE_PARAMS, "role": "invalid"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "division",
    list(CompetitiveDivisionFilter),
)
def test_get_hero_stats_filter_by_competitive_division(
    client: TestClient, division: str
):
    response = client.get(
        "/heroes/stats",
        params={**_COMPETITIVE_PARAMS, "competitive_division": division},
    )

    assert response.status_code == status.HTTP_200_OK


def test_get_hero_stats_filter_by_invalid_competitive_division(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={**_COMPETITIVE_PARAMS, "competitive_division": "invalid"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "order_by",
    [
        "hero:asc",
        "hero:desc",
        "pickrate:asc",
        "pickrate:desc",
        "winrate:asc",
        "winrate:desc",
    ],
)
def test_get_hero_stats_order_by(client: TestClient, order_by: str):
    response = client.get(
        "/heroes/stats", params={**_BASE_PARAMS, "order_by": order_by}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


@pytest.mark.parametrize(
    "order_by",
    ["invalid", "hero", "hero:invalid", "invalid:asc", "pickrate:asc:extra"],
)
def test_get_hero_stats_invalid_order_by(client: TestClient, order_by: str):
    response = client.get(
        "/heroes/stats", params={**_BASE_PARAMS, "order_by": order_by}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_hero_stats_order_by_pickrate_desc_is_sorted(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={**_BASE_PARAMS, "order_by": "pickrate:desc"},
    )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    pickrates = [hero["pickrate"] for hero in data]
    assert pickrates == sorted(pickrates, reverse=True)


def test_get_hero_stats_order_by_hero_asc_is_sorted(client: TestClient):
    response = client.get(
        "/heroes/stats",
        params={**_BASE_PARAMS, "order_by": "hero:asc"},
    )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    heroes = [hero["hero"] for hero in data]
    assert heroes == sorted(heroes)


def test_get_hero_stats_blizzard_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get("/heroes/stats", params=_BASE_PARAMS)

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


def test_get_hero_stats_internal_error(client: TestClient):
    with patch(
        "app.domain.services.hero_service.HeroService.get_hero_stats",
        return_value=([{"invalid_key": "invalid_value"}], False, 0),
    ):
        response = client.get("/heroes/stats", params=_BASE_PARAMS)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"error": settings.internal_server_error_message}


def test_get_hero_stats_blizzard_forbidden_error(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get("/heroes/stats", params=_BASE_PARAMS)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert (
        "Blizzard is temporarily rate limiting this API. Please retry after"
        in response.json()["error"]
    )


def test_get_hero_stats_blizzard_forbidden_error_and_caching(client: TestClient):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_403_FORBIDDEN, text="403 Forbidden"),
    ):
        response1 = client.get("/heroes/stats", params=_BASE_PARAMS)
    response2 = client.get("/heroes/stats", params=_BASE_PARAMS)

    assert (
        response1.status_code
        == response2.status_code
        == status.HTTP_503_SERVICE_UNAVAILABLE
    )
    assert response1.json() == response2.json()
    assert (
        "Blizzard is temporarily rate limiting this API. Please retry after"
        in response1.json()["error"]
    )
