from fastapi import status
from fastapi.testclient import TestClient


def test_get_gamemodes(client: TestClient):
    response = client.get("/gamemodes")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0
