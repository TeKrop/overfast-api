import asyncio

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.common.helpers import overfast_client_settings
from app.common.logging import logger
from app.main import app


class RetryCacheTransport(httpx.AsyncBaseTransport):
    """Transport class for HTTP calls made within the test suite. Main goals :
    - Retry mechanism in case Blizzard is temporarily down, to avoid tests failure
    - Caching mechanism to avoid duplicate HTTP calls across all tests
    """

    def __init__(
        self,
        http_cache: dict[str, httpx.Response],
        retries: int = 3,
        delay: int = 2,
    ):
        self.retries = retries
        self.delay = delay
        self._transport = httpx.AsyncHTTPTransport()
        self._cache = http_cache

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        cache_key = str(request.url)

        logger.info(cache_key)

        if cache_key in self._cache:
            return self._cache[cache_key]

        for attempt in range(self.retries):
            try:
                response = await self._transport.handle_async_request(request)
                if response.status_code not in (
                    status.HTTP_502_BAD_GATEWAY,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ):
                    self._cache[cache_key] = response
                    return response
                logger.info(
                    f"{attempt + 1} attempt failed with HTTP 502, retrying in {self.delay} secondes..."
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (
                    status.HTTP_502_BAD_GATEWAY,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ):
                    raise
            await asyncio.sleep(self.delay)
        raise httpx.HTTPStatusError


@pytest.fixture(scope="session")
def http_cache() -> dict[str, httpx.Response]:
    return {}


@pytest.fixture
def client(http_cache: dict[str, httpx.Response]) -> TestClient:
    transport = RetryCacheTransport(http_cache=http_cache, retries=3, delay=2)
    app.overfast_client = httpx.AsyncClient(
        transport=transport, **overfast_client_settings
    )
    return TestClient(app)
