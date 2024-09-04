import httpx
import pytest
from fastapi.testclient import TestClient

from app.common.helpers import overfast_client_settings
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    app.overfast_client = httpx.AsyncClient(**overfast_client_settings)
    return TestClient(app)
