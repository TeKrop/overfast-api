from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.config import settings
from app.gamemodes.enums import MapGamemode


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


@pytest.mark.parametrize("gamemode", [g.value for g in MapGamemode])
def test_get_maps_filter_by_gamemode(client: TestClient, gamemode: MapGamemode):
    response = client.get("/maps", params={"gamemode": gamemode})
    assert response.status_code == status.HTTP_200_OK
    assert all(gamemode in map_dict["gamemodes"] for map_dict in response.json())


def test_get_maps_invalid_gamemode(client: TestClient):
    response = client.get("/maps", params={"gamemode": "invalid"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
