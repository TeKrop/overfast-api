from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app.config import settings
from app.domain.enums import MapGamemode

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_maps(client: TestClient):
    response = client.get("/maps")
    assert response.status_code == status.HTTP_200_OK

    maps = response.json()
    assert len(maps) > 0, "No maps returned"

    for map_data in maps:
        screenshot_url = map_data["screenshot"]
        screenshot_path = screenshot_url.removeprefix(f"{settings.app_base_url}/")
        path = Path(screenshot_path)
        assert path.is_file(), f"Screenshot file does not exist: {path}"


@pytest.mark.parametrize("gamemode", list(MapGamemode))
def test_get_maps_filter_by_gamemode(client: TestClient, gamemode: MapGamemode):
    response = client.get("/maps", params={"gamemode": gamemode})
    assert response.status_code == status.HTTP_200_OK
    assert all(gamemode in map_dict["gamemodes"] for map_dict in response.json())


def test_get_maps_invalid_gamemode(client: TestClient):
    response = client.get("/maps", params={"gamemode": "invalid"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    ("key", "expected_uses"),
    [
        ("aatlis", ["standard"]),
        ("antarctic-peninsula", ["standard"]),
        ("blizzard-world", ["standard"]),
        ("circuit-royal", ["standard"]),
        ("dorado", ["standard"]),
        ("eichenwalde", ["standard"]),
        ("grimsvotn", ["standard"]),
        ("havana", ["standard"]),
        ("hollywood", ["standard"]),
        ("junkertown", ["standard"]),
        ("kings-row", ["standard"]),
        ("midtown", ["standard"]),
        ("neon-junction", ["standard"]),
        ("new-junk-city", ["standard"]),
        ("new-queen-street", ["standard"]),
        ("numbani", ["standard"]),
        ("paraiso", ["standard"]),
        ("rialto", ["standard"]),
        ("route-66", ["standard"]),
        ("runasapi", ["standard"]),
        ("shambali-monastery", ["standard"]),
        ("suravasa", ["standard"]),
        ("watchpoint-gibraltar", ["standard"]),
        ("anubis", ["arcade"]),
        ("hanamura", ["arcade"]),
        ("horizon", ["arcade"]),
        ("paris", ["arcade"]),
        ("volskaya", ["arcade"]),
        ("practice-range", ["training"]),
        ("ayutthaya", ["arcade"]),
        ("black-forest", ["arcade"]),
        ("castillo", ["arcade"]),
        ("chateau-guillard", ["arcade"]),
        ("ecopoint-antarctica", ["arcade"]),
        ("kanezaka", ["arcade"]),
        ("malevento", ["arcade"]),
        ("necropolis", ["arcade"]),
        ("petra", ["arcade"]),
        ("workshop-chamber", ["workshop"]),
        ("workshop-expanse", ["workshop"]),
        ("workshop-green-screen", ["workshop"]),
        ("workshop-island", ["workshop"]),
        ("arena-victoriae", ["stadium"]),
        ("gogadoro", ["stadium"]),
        ("place-lacroix", ["stadium"]),
        ("redwood-dam", ["stadium"]),
        ("powder-keg-mine", ["stadium"]),
        ("thames-district", ["stadium"]),
        ("busan", ["standard", "stadium"]),
        ("ilios", ["standard", "stadium"]),
        ("lijiang-tower", ["standard", "stadium"]),
        ("nepal", ["standard", "stadium"]),
        ("oasis", ["standard", "stadium"]),
        ("samoa", ["standard", "stadium"]),
        ("wuxing-university", ["stadium"]),
        ("colosseo", ["standard", "stadium"]),
        ("esperanca", ["standard", "stadium"]),
        ("hanaoka", ["arcade"]),
        ("throne-of-anubis", ["arcade"]),
    ],
)
def test_get_maps_uses(client: TestClient, key: str, expected_uses: list[str]) -> None:
    url = "/maps"

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert next(m for m in response.json() if m["key"] == key)["uses"] == expected_uses
    assert all(
        m["uses"]
        in (
            ["standard"],
            ["stadium"],
            ["standard", "stadium"],
            ["workshop"],
            ["arcade"],
            ["training"],
        )
        for m in response.json()
    )
