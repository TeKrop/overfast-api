"""Blizzard HTTP client adapter implementing BlizzardClientPort"""

import time

import httpx
from fastapi import HTTPException, status

from app.adapters.blizzard.throttle import BlizzardThrottle
from app.config import settings
from app.exceptions import RateLimitedError
from app.metaclasses import Singleton
from app.monitoring.helpers import normalize_blizzard_url
from app.monitoring.metrics import (
    blizzard_request_duration_seconds,
    blizzard_requests_total,
)
from app.overfast_logger import logger


class BlizzardClient(metaclass=Singleton):
    """
    HTTP client for Blizzard API/web requests with adaptive throttling.

    Implements BlizzardClientPort protocol via structural typing (duck typing).
    Protocol compliance is verified by type checkers at injection points.
    """

    def __init__(self):
        self.throttle = BlizzardThrottle() if settings.throttle_enabled else None
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    f"OverFastAPI v{settings.app_version} - "
                    "https://github.com/TeKrop/overfast-api"
                ),
                "From": "valentin.porchet@proton.me",
            },
            http2=True,
            timeout=10,
            follow_redirects=True,
        )

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an HTTP GET request, respecting the adaptive throttle."""
        if self.throttle:
            await self._throttle_wait()

        kwargs: dict = {}
        if headers:
            kwargs["headers"] = headers
        if params:
            kwargs["params"] = params

        normalized_endpoint = normalize_blizzard_url(url)
        response, duration = await self._execute_request(
            url, normalized_endpoint, kwargs
        )

        if self.throttle:
            await self.throttle.adjust_delay(duration, response.status_code)

        logger.debug("OverFast request done!")

        if response.status_code == status.HTTP_403_FORBIDDEN:
            raise self._blizzard_rate_limited_error()

        return response

    async def _throttle_wait(self) -> None:
        """Check throttle before request; raise 503 if in penalty period."""
        if not self.throttle:
            return

        try:
            await self.throttle.wait_before_request()
        except RateLimitedError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Blizzard is temporarily rate limiting this API. "
                    f"Please retry after {exc.retry_after} seconds."
                ),
                headers={settings.retry_after_header: str(exc.retry_after)},
            ) from exc

    async def _execute_request(
        self,
        url: str,
        normalized_endpoint: str,
        kwargs: dict,
    ) -> tuple[httpx.Response, float]:
        """Execute the HTTP GET and record metrics. Returns (response, duration)."""
        start_time = time.perf_counter()
        try:
            response = await self.client.get(url, **kwargs)
        except httpx.TimeoutException as error:
            duration = time.perf_counter() - start_time
            self._record_metrics(normalized_endpoint, "timeout", duration)
            raise self._blizzard_response_error(
                status_code=0,
                error="Blizzard took more than 10 seconds to respond, resulting in a timeout",
            ) from error
        except httpx.RemoteProtocolError as error:
            duration = time.perf_counter() - start_time
            self._record_metrics(normalized_endpoint, "error", duration)
            raise self._blizzard_response_error(
                status_code=0,
                error="Blizzard closed the connection, no data could be retrieved",
            ) from error

        duration = time.perf_counter() - start_time
        self._record_metrics(normalized_endpoint, str(response.status_code), duration)
        return response, duration

    @staticmethod
    def _record_metrics(endpoint: str, status_label: str, duration: float) -> None:
        if settings.prometheus_enabled:
            blizzard_requests_total.labels(endpoint=endpoint, status=status_label).inc()
            blizzard_request_duration_seconds.labels(endpoint=endpoint).observe(
                duration
            )

    async def close(self) -> None:
        """Properly close HTTPX Async Client"""
        await self.client.aclose()

    # Legacy alias for backward compatibility
    async def aclose(self) -> None:
        """Alias for close() - deprecated, use close() instead"""
        await self.close()

    def blizzard_response_error_from_response(
        self, response: httpx.Response
    ) -> HTTPException:
        """Alias for sending Blizzard error from a request directly"""
        return self._blizzard_response_error(response.status_code, response.text)

    @staticmethod
    def _blizzard_response_error(status_code: int, error: str) -> HTTPException:
        """Retrieve a generic error response when a Blizzard page doesn't load"""
        logger.error(
            "Received an error from Blizzard. HTTP {} : {}",
            status_code,
            error,
        )
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Couldn't get Blizzard page (HTTP {status_code} error) : {error}",
        )

    @staticmethod
    def _blizzard_rate_limited_error() -> HTTPException:
        """Return 503 when Blizzard is rate limiting us (HTTP 403 received).

        The throttle has already recorded the penalty and adjusted the delay.
        """
        retry_after = settings.throttle_penalty_duration
        logger.warning(
            "[BlizzardClient] Rate limited by Blizzard (403) — returning 503 to client"
        )
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Blizzard is temporarily rate limiting this API. "
                f"Please retry after {retry_after} seconds."
            ),
            headers={settings.retry_after_header: str(retry_after)},
        )


# Backward compatibility alias
OverFastClient = BlizzardClient
