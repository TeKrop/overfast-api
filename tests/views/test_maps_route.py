import pytest
from fastapi.testclient import TestClient

from overfastapi.common.enums import MapGamemode
from overfastapi.config import OVERFAST_API_BASE_URL
from overfastapi.main import app

client = TestClient(app)


def test_get_maps(maps_json_data: list):
    response = client.get("/maps")
    json_response = response.json()
    assert response.status_code == 200
    assert json_response == maps_json_data

    # Check if all the images link are valid
    for map_dict in json_response:
        image_response = client.get(
            map_dict["screenshot"].removeprefix(OVERFAST_API_BASE_URL)
        )
        assert image_response.status_code == 200


@pytest.mark.parametrize("gamemode", [g.value for g in MapGamemode])
def test_get_maps_filter_by_gamemode(gamemode: MapGamemode, maps_json_data: list):
    response = client.get(f"/maps?gamemode={gamemode}")
    assert response.status_code == 200
    assert response.json() == [
        map_dict for map_dict in maps_json_data if gamemode in map_dict["gamemodes"]
    ]


def test_get_maps_invalid_role():
    response = client.get("/maps?gamemode=invalid")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["query", "gamemode"],
                "msg": (
                    "value is not a valid enumeration member; "
                    "permitted: 'assault', 'capture-the-flag', 'control', "
                    "'deathmatch', 'elimination', 'escort', 'hybrid', 'push', "
                    "'team-deathmatch'"
                ),
                "type": "type_error.enum",
                "ctx": {
                    "enum_values": [
                        "assault",
                        "capture-the-flag",
                        "control",
                        "deathmatch",
                        "elimination",
                        "escort",
                        "hybrid",
                        "push",
                        "team-deathmatch",
                    ]
                },
            }
        ]
    }


def test_get_maps_images(maps_json_data: list):
    response = client.get("/maps")
    assert response.status_code == 200
    assert response.json() == maps_json_data
