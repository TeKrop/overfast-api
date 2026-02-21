from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import TimeoutException

from app.config import settings
from app.players.enums import HeroKeyCareerFilter, PlayerGamemode, PlayerPlatform

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _setup_player_stats_test(
    player_html_data: str,
    player_search_response_mock: Mock,
):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=[
            # Players search call first
            player_search_response_mock,
            # Player profile page
            Mock(status_code=status.HTTP_200_OK, text=player_html_data),
        ],
    ):
        yield


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={"gamemode": PlayerGamemode.QUICKPLAY},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_valid_hero(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={
            "gamemode": PlayerGamemode.QUICKPLAY,
            "hero": HeroKeyCareerFilter.ANA,  # ty: ignore[unresolved-attribute]
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert set(response.json().keys()) == {HeroKeyCareerFilter.ANA}  # ty: ignore[unresolved-attribute]


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_invalid_hero(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={
            "gamemode": PlayerGamemode.QUICKPLAY,
            "hero": "invalid_hero",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_missing_gamemode(client: TestClient, uri: str):
    response = client.get(f"/players/TeKrop-2217{uri}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_invalid_gamemode(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={"gamemode": "invalid_gamemode"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_valid_platform(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={
            "gamemode": PlayerGamemode.QUICKPLAY,
            "platform": PlayerPlatform.PC,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().keys()) > 0


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_empty_platform(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={
            "gamemode": PlayerGamemode.QUICKPLAY,
            "platform": PlayerPlatform.CONSOLE,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_invalid_platform(client: TestClient, uri: str):
    response = client.get(
        f"/players/TeKrop-2217{uri}",
        params={
            "gamemode": PlayerGamemode.QUICKPLAY,
            "platform": "invalid_platform",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_blizzard_error(client: TestClient, uri: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            text="Service Unavailable",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": "Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    }


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_blizzard_timeout(client: TestClient, uri: str):
    with patch(
        "httpx.AsyncClient.get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert response.json() == {
        "error": (
            "Couldn't get Blizzard page (HTTP 0 error) : "
            "Blizzard took more than 10 seconds to respond, resulting in a timeout"
        ),
    }


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(("uri"), [("/stats"), ("/stats/career")])
def test_get_player_stats_blizzard_forbidden_error(client: TestClient, uri: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(
            status_code=status.HTTP_403_FORBIDDEN,
            text="403 Forbidden",
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {
        "error": (
            "API has been rate limited by Blizzard, please wait for "
            f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
        )
    }


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
@pytest.mark.parametrize(
    ("uri", "patch_target"),
    [
        (
            "/stats",
            "app.domain.services.player_service.PlayerService.get_player_stats",
        ),
        (
            "/stats/career",
            "app.domain.services.player_service.PlayerService.get_player_career_stats",
        ),
    ],
)
def test_get_player_stats_internal_error(
    client: TestClient, uri: str, patch_target: str
):
    with patch(
        patch_target,
        return_value=(
            {
                "ana": [{"category": "invalid_value", "stats": [{"key": "test"}]}],
            },
            False,
        ),
    ):
        response = client.get(
            f"/players/TeKrop-2217{uri}",
            params={"gamemode": PlayerGamemode.QUICKPLAY},
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"error": settings.internal_server_error_message}
