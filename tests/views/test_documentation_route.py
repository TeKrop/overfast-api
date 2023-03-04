import re

from fastapi import status
from fastapi.testclient import TestClient

from overfastapi.main import app

client = TestClient(app)


def test_get_documentation():
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert (
        re.search("<title>(.*)</title>", response.text, re.IGNORECASE).group(1)
        == "OverFast API - Documentation"
    )
