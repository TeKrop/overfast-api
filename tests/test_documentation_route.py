import re
from typing import TYPE_CHECKING

from fastapi import status

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_redoc_documentation(client: TestClient):
    response = client.get("/")

    title_search = re.search("<title>(.*)</title>", response.text, re.IGNORECASE)

    assert response.status_code == status.HTTP_200_OK
    assert title_search is not None
    assert title_search[1] == "OverFast API - Documentation"


def test_get_swagger_documentation(client: TestClient):
    response = client.get("/docs")

    title_search = re.search("<title>(.*)</title>", response.text, re.IGNORECASE)

    assert response.status_code == status.HTTP_200_OK
    assert title_search is not None
    assert title_search[1] == "OverFast API - Documentation"
