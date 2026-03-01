"""Adaptive throttle controller for Blizzard HTTP requests.

Implements a hybrid AutoThrottle + AIMD strategy:

* **AutoThrottle** (primary): adjusts inter-request delay based on observed
  response latency so that we never saturate Blizzard's rate limiter.
  ``target_delay = latency / target_concurrency``

* **AIMD penalty** (secondary): when Blizzard returns 403, the delay is
  immediately doubled (minimum ``throttle_penalty_delay``) and recovery is
  blocked for ``throttle_penalty_duration`` seconds.

State is stored in Valkey so the API process and the worker process share
the same throttle state.
"""

import asyncio
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

from app.adapters.cache.valkey_cache import ValkeyCache
from app.api.helpers import send_discord_webhook_message
from app.config import settings
from app.domain.exceptions import RateLimitedError
from app.infrastructure.logger import logger
from app.metaclasses import Singleton
from app.monitoring.metrics import (
    throttle_403_total,
    throttle_current_delay_seconds,
    throttle_wait_seconds,
)

if TYPE_CHECKING:
    from app.domain.ports.cache import CachePort

_DELAY_KEY = "throttle:delay"
_LAST_403_KEY = "throttle:last_403"
_LAST_REQUEST_KEY = "throttle:last_request"


class BlizzardThrottle(metaclass=Singleton):
    """Shared-state adaptive throttle for Blizzard requests.

    Uses Valkey to share ``throttle:delay``, ``throttle:last_403``, and
    ``throttle:last_request`` between the FastAPI process and the worker.
    An in-process ``_penalty_start`` attribute provides fast, I/O-free penalty
    detection within the same process instance.
    """

    def __init__(self) -> None:
        self._cache: CachePort = ValkeyCache()
        self._penalty_start: float | None = None

    async def get_current_delay(self) -> float:
        """Return the current inter-request delay (seconds)."""
        raw = await self._cache.get(_DELAY_KEY)
        return float(raw) if raw else settings.throttle_start_delay

    async def is_rate_limited(self) -> int:
        """Return remaining penalty seconds; 0 if not currently rate-limited.

        Checks the in-process ``_penalty_start`` first (no I/O) before falling
        back to Valkey for cross-process awareness (e.g., from the worker).
        """
        # Fast in-process check (avoids Valkey round-trip in the common case)
        if self._penalty_start is not None:
            elapsed = time.monotonic() - self._penalty_start
            remaining = settings.throttle_penalty_duration - elapsed
            if remaining > 0:
                return int(remaining)
            self._penalty_start = None  # penalty expired

        # Cross-process check via Valkey (e.g. worker set the penalty)
        raw = await self._cache.get(_LAST_403_KEY)
        if not raw:
            return 0
        elapsed = time.time() - float(raw)
        remaining = settings.throttle_penalty_duration - elapsed
        return max(0, int(remaining))

    async def wait_before_request(self) -> None:
        """Sleep for the current throttle delay, or raise RateLimitedError if in penalty.

        Raises:
            RateLimitedError: if the penalty period is still active.
        """
        remaining = await self.is_rate_limited()
        if remaining > 0:
            raise RateLimitedError(retry_after=remaining)

        delay = await self.get_current_delay()
        raw_last = await self._cache.get(_LAST_REQUEST_KEY)
        if raw_last:
            wait = max(0.0, delay - (time.time() - float(raw_last)))
            if wait > 0:
                if settings.prometheus_enabled:
                    throttle_wait_seconds.observe(wait)
                logger.debug(
                    f"[Throttle] Waiting {wait:.2f}s before next Blizzard request"
                )
                await asyncio.sleep(wait)

        await self._cache.set(_LAST_REQUEST_KEY, str(time.time()).encode())

    async def adjust_delay(self, latency: float, status_code: int) -> None:
        """Update the throttle delay based on the observed response.

        * **200**: AutoThrottle — converge toward ``latency / target_concurrency``.
        * **403**: AIMD penalty — double delay (min ``penalty_delay``), block recovery.
        * **other non-200**: conservative — only allow delay to increase.

        Args:
            latency: Elapsed seconds from request start to response received.
            status_code: HTTP status code of the Blizzard response.
        """
        current = await self.get_current_delay()

        if status_code == HTTPStatus.FORBIDDEN:
            await self._apply_403_penalty(current)
            return

        in_penalty = (await self.is_rate_limited()) > 0

        if status_code == HTTPStatus.OK and not in_penalty:
            await self._autothrottle_adjust(latency, current)
        elif status_code != HTTPStatus.OK:
            await self._conservative_increase(latency, current)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _apply_403_penalty(self, current_delay: float) -> None:
        new_delay = min(
            max(current_delay * 2, settings.throttle_penalty_delay),
            settings.throttle_max_delay,
        )
        await self._cache.set(_DELAY_KEY, str(new_delay).encode())
        await self._cache.set(_LAST_403_KEY, str(time.time()).encode())
        self._penalty_start = time.monotonic()

        if settings.prometheus_enabled:
            throttle_current_delay_seconds.set(new_delay)
            throttle_403_total.inc()

        logger.warning(
            f"[Throttle] Blizzard 403 — delay {current_delay:.2f}s → {new_delay:.2f}s "
            f"(penalty {settings.throttle_penalty_duration}s)"
        )

        if settings.discord_message_on_rate_limit:
            send_discord_webhook_message(
                title="⚠️ Blizzard Rate Limit Reached",
                description="Throttle penalty activated — backing off Blizzard requests.",
                fields=[
                    {"name": "New Delay", "value": f"{new_delay:.1f}s", "inline": True},
                    {
                        "name": "Penalty Duration",
                        "value": f"{settings.throttle_penalty_duration}s",
                        "inline": True,
                    },
                ],
                color=0xF39C12,
            )

    async def _autothrottle_adjust(self, latency: float, current_delay: float) -> None:
        target = latency / settings.throttle_target_concurrency
        # Smooth toward target but bias upward (conservative)
        new_delay = max(target, (current_delay + target) / 2.0)
        new_delay = max(
            settings.throttle_min_delay, min(new_delay, settings.throttle_max_delay)
        )
        await self._cache.set(_DELAY_KEY, str(new_delay).encode())

        if settings.prometheus_enabled:
            throttle_current_delay_seconds.set(new_delay)

        logger.debug(
            f"[Throttle] AutoThrottle: {current_delay:.2f}s → {new_delay:.2f}s "
            f"(latency={latency:.2f}s)"
        )

    async def _conservative_increase(
        self, latency: float, current_delay: float
    ) -> None:
        target = latency / settings.throttle_target_concurrency
        if target > current_delay:
            new_delay = min(target, settings.throttle_max_delay)
            await self._cache.set(_DELAY_KEY, str(new_delay).encode())

            if settings.prometheus_enabled:
                throttle_current_delay_seconds.set(new_delay)

            logger.warning(
                f"[Throttle] Non-200 conservative increase: "
                f"{current_delay:.2f}s → {new_delay:.2f}s"
            )
