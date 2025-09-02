from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient

from app.config import settings


def test_get_gamemodes(client: TestClient):
    response = client.get("/gamemodes")
    assert response.status_code == status.HTTP_200_OK

    gamemodes = response.json()
    assert len(gamemodes) > 0, "No gamemodes returned"

    for gamemode in gamemodes:
        for image_key in ("icon", "screenshot"):
            image_url = gamemode[image_key]
            image_path = image_url.removeprefix(f"{settings.app_base_url}/")
            path = Path(image_path)
            assert path.is_file(), f"{image_key} file does not exist: {path}"
