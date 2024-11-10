import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.gamemodes.enums import MapGamemode


def test_get_maps(client: TestClient):
    response = client.get("/maps")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


@pytest.mark.parametrize("gamemode", [g.value for g in MapGamemode])
def test_get_maps_filter_by_gamemode(client: TestClient, gamemode: MapGamemode):
    response = client.get(f"/maps?gamemode={gamemode}")
    assert response.status_code == status.HTTP_200_OK
    assert all(gamemode in map_dict["gamemodes"] for map_dict in response.json())


def test_get_maps_invalid_gamemode(client: TestClient):
    response = client.get("/maps?gamemode=invalid")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
