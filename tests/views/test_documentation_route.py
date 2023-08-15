import re

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_redoc_documentation():
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert (
        re.search("<title>(.*)</title>", response.text, re.IGNORECASE)[1]
        == "OverFast API - Documentation"
    )


def test_get_swagger_documentation():
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
    assert (
        re.search("<title>(.*)</title>", response.text, re.IGNORECASE)[1]
        == "OverFast API - Documentation"
    )
