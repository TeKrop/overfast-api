import re

from fastapi.testclient import TestClient

from overfastapi.main import app

client = TestClient(app)


def test_get_documentation():
    response = client.get("/")
    assert response.status_code == 200
    assert (
        re.search("<title>(.*)</title>", response.text, re.IGNORECASE).group(1)
        == "OverFast API - Documentation"
    )
