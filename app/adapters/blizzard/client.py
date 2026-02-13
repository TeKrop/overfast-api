"""Blizzard HTTP client adapter implementing BlizzardClientPort"""

import time

import httpx
from fastapi import HTTPException, status

from app.adapters.cache import CacheManager
from app.config import settings
from app.helpers import send_discord_webhook_message
from app.metaclasses import Singleton
from app.monitoring.helpers import normalize_blizzard_url
from app.monitoring.metrics import (
    blizzard_rate_limited_total,
    blizzard_request_duration_seconds,
    blizzard_requests_total,
)
from app.overfast_logger import logger


class BlizzardClient(metaclass=Singleton):
    """
    HTTP client for Blizzard API/web requests with rate limiting.

    Implements BlizzardClientPort protocol via structural typing (duck typing).
    Protocol compliance is verified by type checkers at injection points.
    """

    def __init__(self):
        self.cache_manager = CacheManager()
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
        """Make an HTTP GET request with custom headers and retrieve the result"""

        # First, check if we're being rate limited
        self._check_rate_limit()

        # Prepare kwargs
        kwargs = {}
        if headers:
            kwargs["headers"] = headers
        if params:
            kwargs["params"] = params

        # Normalize URL for metrics labels
        normalized_endpoint = normalize_blizzard_url(url)

        # Make the API call
        start_time = time.perf_counter()
        try:
            response = await self.client.get(url, **kwargs)
        except httpx.TimeoutException as error:
            duration = time.perf_counter() - start_time
            if settings.prometheus_enabled:
                blizzard_requests_total.labels(
                    endpoint=normalized_endpoint, status="timeout"
                ).inc()
                blizzard_request_duration_seconds.labels(
                    endpoint=normalized_endpoint
                ).observe(duration)
            raise self._blizzard_response_error(
                status_code=0,
                error="Blizzard took more than 10 seconds to respond, resulting in a timeout",
            ) from error
        except httpx.RemoteProtocolError as error:
            duration = time.perf_counter() - start_time
            if settings.prometheus_enabled:
                blizzard_requests_total.labels(
                    endpoint=normalized_endpoint, status="error"
                ).inc()
                blizzard_request_duration_seconds.labels(
                    endpoint=normalized_endpoint
                ).observe(duration)
            raise self._blizzard_response_error(
                status_code=0,
                error="Blizzard closed the connection, no data could be retrieved",
            ) from error

        duration = time.perf_counter() - start_time
        if settings.prometheus_enabled:
            blizzard_requests_total.labels(
                endpoint=normalized_endpoint, status=str(response.status_code)
            ).inc()
            blizzard_request_duration_seconds.labels(
                endpoint=normalized_endpoint
            ).observe(duration)

        logger.debug("OverFast request done !")

        # Make sure we catch HTTP 403 from Blizzard when it happens,
        # so we don't make any more call before some amount of time
        if response.status_code == status.HTTP_403_FORBIDDEN:
            raise self._blizzard_forbidden_error()

        return response

    async def close(self) -> None:
        """Properly close HTTPX Async Client"""
        await self.client.aclose()

    # Legacy alias for backward compatibility
    async def aclose(self) -> None:
        """Alias for close() - deprecated, use close() instead"""
        await self.close()

    def _check_rate_limit(self) -> None:
        """Make sure we're not being rate limited by Blizzard before making
        any API call. Else, return an HTTP 429 with Retry-After header.
        """
        if self.cache_manager.is_being_rate_limited():
            raise self._too_many_requests_response(
                retry_after=self.cache_manager.get_global_rate_limit_remaining_time()
            )

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

    def _blizzard_forbidden_error(self) -> HTTPException:
        """Retrieve a generic error response when Blizzard returns forbidden error.
        Also prevent further calls to Blizzard for a given amount of time.
        """

        # We have to block future requests to Blizzard, cache the information on Valkey
        self.cache_manager.set_global_rate_limit()

        # Track rate limit event
        if settings.prometheus_enabled:
            blizzard_rate_limited_total.inc()

        # If Discord Webhook configuration is enabled, send a message to the
        # given channel using Discord Webhook URL
        if settings.discord_message_on_rate_limit:
            send_discord_webhook_message(
                title="⚠️ Blizzard Rate Limit Reached",
                description="Blocking further calls to Blizzard API.",
                fields=[
                    {
                        "name": "Retry After",
                        "value": f"{settings.blizzard_rate_limit_retry_after} seconds",
                        "inline": True,
                    },
                ],
                color=0xF39C12,  # Orange/Warning color
            )

        return self._too_many_requests_response(
            retry_after=settings.blizzard_rate_limit_retry_after
        )

    @staticmethod
    def _too_many_requests_response(retry_after: int) -> HTTPException:
        """Generic method to return an HTTP 429 response with Retry-After header"""
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "API has been rate limited by Blizzard, please wait for "
                f"{retry_after} seconds before retrying"
            ),
            headers={settings.retry_after_header: str(retry_after)},
        )


# Backward compatibility alias
OverFastClient = BlizzardClient
