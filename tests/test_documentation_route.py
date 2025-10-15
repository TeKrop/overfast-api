import re
from typing import TYPE_CHECKING

from fastapi import status

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_redoc_documentation(client: TestClient):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert (
        re.search("<title>(.*)</title>", response.text, re.IGNORECASE)[1]
        == "OverFast API - Documentation"
    )


def test_get_swagger_documentation(client: TestClient):
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
    assert (
        re.search("<title>(.*)</title>", response.text, re.IGNORECASE)[1]
        == "OverFast API - Documentation"
    )
