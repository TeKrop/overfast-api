import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    app.overfast_client = httpx.AsyncClient()
    return TestClient(app)
