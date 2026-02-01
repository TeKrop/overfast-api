"""OverFast HTTP Client with adaptive rate limiting and metrics tracking"""

import asyncio
import time
from collections import deque
from typing import Any

import httpx
from fastapi import HTTPException, status

from .cache_manager import CacheManager
from .config import settings
from .helpers import send_discord_webhook_message
from .metaclasses import Singleton
from .overfast_logger import logger


class BlizzardRequestMetrics:
    """Metrics tracker for Blizzard API requests with real-time monitoring capabilities"""

    # Time window for calculating requests per second (in seconds)
    METRICS_TIME_WINDOW = 60

    def __init__(self):
        # Current state
        self.active_requests = 0
        self.max_concurrent_requests = 0

        # Historical data (last 1000 requests, roughly last few minutes)
        self.request_history: deque = deque(maxlen=1000)

        # Lifetime counters
        self.total_requests = 0
        self.total_rate_limited = 0
        self.total_errors = 0
        self.total_timeouts = 0

        # Response time tracking
        self.total_response_time = 0.0
        self.min_response_time = float("inf")
        self.max_response_time = 0.0

        # Thread safety
        self._lock = asyncio.Lock()

    async def record_request_start(self) -> float:
        """Record the start of a request and return start time"""
        async with self._lock:
            self.active_requests += 1
            self.total_requests += 1
            self.max_concurrent_requests = max(
                self.max_concurrent_requests, self.active_requests
            )
        return time.time()

    async def record_request_end(
        self,
        start_time: float,
        status_code: int | None = None,
        was_rate_limited: bool = False,
        was_error: bool = False,
        was_timeout: bool = False,
    ) -> None:
        """Record the end of a request with metrics"""
        end_time = time.time()
        response_time = end_time - start_time

        async with self._lock:
            self.active_requests = max(0, self.active_requests - 1)

            # Update response time metrics
            self.total_response_time += response_time
            self.min_response_time = min(self.min_response_time, response_time)
            self.max_response_time = max(self.max_response_time, response_time)

            # Update error counters
            if was_rate_limited:
                self.total_rate_limited += 1
            if was_error:
                self.total_errors += 1
            if was_timeout:
                self.total_timeouts += 1

            # Store in history
            self.request_history.append(
                {
                    "timestamp": end_time,
                    "response_time": response_time,
                    "status_code": status_code,
                    "rate_limited": was_rate_limited,
                    "error": was_error,
                    "timeout": was_timeout,
                }
            )

    async def get_stats(self) -> dict[str, Any]:
        """Get current statistics"""
        async with self._lock:
            # Calculate requests per second over last 60 seconds
            now = time.time()
            recent_requests = [
                r
                for r in self.request_history
                if now - r["timestamp"] <= self.METRICS_TIME_WINDOW
            ]
            requests_per_second = (
                len(recent_requests) / self.METRICS_TIME_WINDOW
                if recent_requests
                else 0
            )

            # Calculate average response time
            avg_response_time = (
                self.total_response_time / self.total_requests
                if self.total_requests > 0
                else 0
            )

            return {
                "active_requests": self.active_requests,
                "max_concurrent_requests": self.max_concurrent_requests,
                "total_requests": self.total_requests,
                "total_rate_limited": self.total_rate_limited,
                "total_errors": self.total_errors,
                "total_timeouts": self.total_timeouts,
                "requests_per_second_last_60s": round(requests_per_second, 2),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
                "min_response_time_ms": round(self.min_response_time * 1000, 2)
                if self.min_response_time != float("inf")
                else 0,
                "max_response_time_ms": round(self.max_response_time * 1000, 2),
                "rate_limit_percentage": round(
                    (self.total_rate_limited / self.total_requests * 100)
                    if self.total_requests > 0
                    else 0,
                    2,
                ),
            }

    async def reset_peak_metrics(self) -> None:
        """Reset peak metrics (useful for monitoring specific periods)"""
        async with self._lock:
            self.max_concurrent_requests = self.active_requests


class AdaptiveRateLimiter:
    """Adaptive rate limiter using AIMD (Additive Increase Multiplicative Decrease) algorithm"""

    def __init__(
        self,
        initial_rate: float = 10.0,
        min_rate: float = 1.0,
        max_rate: float = 50.0,
        decrease_factor: float = 0.5,
        increase_step: float = 0.5,
    ):
        self.current_rate = initial_rate  # requests per second
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.decrease_factor = decrease_factor
        self.increase_step = increase_step

        # Track last request time for rate limiting
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait if necessary to respect rate limit"""
        async with self._lock:
            now = time.time()
            min_interval = 1.0 / self.current_rate
            time_since_last = now - self.last_request_time

            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    async def on_success(self) -> None:
        """Called when a request succeeds - gradually increase rate"""
        async with self._lock:
            old_rate = self.current_rate
            self.current_rate = min(
                self.max_rate, self.current_rate + self.increase_step
            )
            if old_rate != self.current_rate:
                logger.debug(
                    "Rate limit increased: {:.2f} -> {:.2f} req/s",
                    old_rate,
                    self.current_rate,
                )

    async def on_rate_limit(self) -> None:
        """Called when rate limited - decrease rate quickly"""
        async with self._lock:
            old_rate = self.current_rate
            self.current_rate = max(
                self.min_rate, self.current_rate * self.decrease_factor
            )
            logger.warning(
                "Rate limit hit! Decreasing rate: {:.2f} -> {:.2f} req/s",
                old_rate,
                self.current_rate,
            )

    async def get_current_rate(self) -> float:
        """Get current rate limit"""
        async with self._lock:
            return self.current_rate


class OverFastClient(metaclass=Singleton):
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

        # Initialize metrics and rate limiter
        self.metrics = BlizzardRequestMetrics()
        self.rate_limiter = AdaptiveRateLimiter(
            initial_rate=settings.blizzard_initial_rate_limit,
            min_rate=settings.blizzard_min_rate_limit,
            max_rate=settings.blizzard_max_rate_limit,
            decrease_factor=settings.blizzard_rate_decrease_factor,
            increase_step=settings.blizzard_rate_increase_step,
        )

        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(settings.blizzard_max_concurrent_requests)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make an HTTP GET request with adaptive rate limiting and metrics tracking"""

        # Acquire semaphore to limit concurrent requests
        async with self.semaphore:
            # Wait for rate limiter
            await self.rate_limiter.acquire()

            # Track metrics
            start_time = await self.metrics.record_request_start()
            was_rate_limited = False
            was_error = False
            was_timeout = False
            response_status = None

            try:
                # Make the API call
                response = await self.client.get(url, **kwargs)
                response_status = response.status_code

                logger.debug("OverFast request done ! Status: {}", response.status_code)

                # Handle rate limiting
                if response.status_code == status.HTTP_403_FORBIDDEN:
                    was_rate_limited = True
                    await self.rate_limiter.on_rate_limit()
                    raise self._blizzard_forbidden_error()

                # On success, gradually increase rate
                if response.status_code == status.HTTP_200_OK:
                    await self.rate_limiter.on_success()

            except httpx.TimeoutException as error:
                was_timeout = True
                raise self._blizzard_response_error(
                    status_code=0,
                    error="Blizzard took more than 10 seconds to respond, resulting in a timeout",
                ) from error
            except httpx.RemoteProtocolError as error:
                was_error = True
                raise self._blizzard_response_error(
                    status_code=0,
                    error="Blizzard closed the connection, no data could be retrieved",
                ) from error
            else:
                # Return response for all other non-403 status codes
                return response
            finally:
                await self.metrics.record_request_end(
                    start_time=start_time,
                    status_code=response_status,
                    was_rate_limited=was_rate_limited,
                    was_error=was_error,
                    was_timeout=was_timeout,
                )

    async def get_metrics(self) -> dict[str, Any]:
        """Get current metrics for monitoring"""
        stats = await self.metrics.get_stats()
        current_rate = await self.rate_limiter.get_current_rate()

        return {
            **stats,
            "current_rate_limit": round(current_rate, 2),
            "max_concurrent_limit": settings.blizzard_max_concurrent_requests,
        }

    async def reset_metrics(self) -> None:
        """Reset peak metrics for monitoring"""
        await self.metrics.reset_peak_metrics()

    async def aclose(self) -> None:
        """Properly close HTTPX Async Client"""
        await self.client.aclose()

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
        Note: With adaptive rate limiting, we no longer block all users globally,
        but we keep the same error code/message for backward compatibility.
        """

        # If Discord Webhook configuration is enabled, send a message
        if settings.discord_webhook_enabled:
            send_discord_webhook_message(
                f"Blizzard Rate Limit reached! Current rate: "
                f"{self.rate_limiter.current_rate:.2f} req/s"
            )

        # Return HTTP 429 with original message for backward compatibility
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "API has been rate limited by Blizzard, please wait for "
                f"{settings.blizzard_rate_limit_retry_after} seconds before retrying"
            ),
            headers={
                settings.retry_after_header: str(
                    settings.blizzard_rate_limit_retry_after
                )
            },
        )
