from fastapi import status
from fastapi.testclient import TestClient


def test_get_gamemodes(client: TestClient, gamemodes_json_data: list):
    response = client.get("/gamemodes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == gamemodes_json_data
