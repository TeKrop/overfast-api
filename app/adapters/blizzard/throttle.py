"""Adaptive throttle controller for Blizzard HTTP requests.

Implements a TCP Slow Start + AIMD strategy:

* **Slow Start**: while the inter-request delay is above the slow-start
  threshold (``ssthresh``), halve the delay every
  ``throttle_slow_start_n_successes`` consecutive 200 responses.

* **AIMD** (Additive Increase / Multiplicative Decrease): once the delay
  reaches or drops below ``ssthresh``, reduce the delay by
  ``throttle_aimd_delta`` every ``throttle_aimd_n_successes`` consecutive
  200 responses.  On a 403, immediately double the delay (minimum
  ``throttle_penalty_delay``), update ``ssthresh``, and block recovery for
  ``throttle_penalty_duration`` seconds.

State is stored in Valkey so the API process and the worker process share
the same throttle state.
"""

import asyncio
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

from app.adapters.cache.valkey_cache import ValkeyCache
from app.config import settings
from app.domain.exceptions import RateLimitedError
from app.infrastructure.helpers import send_discord_webhook_message
from app.infrastructure.logger import logger
from app.infrastructure.metaclasses import Singleton
from app.monitoring.metrics import (
    blizzard_rate_limited_total,
    throttle_403_total,
    throttle_current_delay_seconds,
    throttle_wait_seconds,
)

if TYPE_CHECKING:
    from app.domain.ports.cache import CachePort

_DELAY_KEY = "throttle:delay"
_SSTHRESH_KEY = "throttle:ssthresh"
_STREAK_KEY = "throttle:streak"
_LAST_403_KEY = "throttle:last_403"
_LAST_REQUEST_KEY = "throttle:last_request"


class BlizzardThrottle(metaclass=Singleton):
    """Shared-state adaptive throttle for Blizzard requests.

    Uses Valkey to share throttle state between the FastAPI process and the
    worker.  An in-process ``_penalty_start`` attribute provides fast,
    I/O-free penalty detection within the same process instance.
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
        if remaining > 0:
            # Sync the in-process monotonic clock so subsequent calls bypass Valkey.
            self._penalty_start = time.monotonic() - elapsed
            return int(remaining)
        return 0

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
                    "[Throttle] Waiting {:.2f}s before next Blizzard request", wait
                )
                await asyncio.sleep(wait)

        await self._cache.set(_LAST_REQUEST_KEY, str(time.time()).encode())

    async def adjust_delay(self, status_code: int) -> None:
        """Update the throttle delay based on the observed response.

        * **200**: TCP Slow Start / AIMD — gradually reduce delay on success.
        * **403**: Multiplicative increase — double delay, set ssthresh.
        * **other non-200**: reset streak only (not a rate-limit signal).

        Args:
            latency: Kept for interface compatibility; not used in this implementation.
            status_code: HTTP status code of the Blizzard response.
        """
        if status_code == HTTPStatus.FORBIDDEN:
            await self._apply_403_penalty()
            return
        if status_code == HTTPStatus.OK:
            in_penalty = (await self.is_rate_limited()) > 0
            if not in_penalty:
                await self._on_success()
            return
        # non-200, non-403: reset streak only
        await self._cache.set(_STREAK_KEY, b"0")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_ssthresh(self) -> float:
        raw = await self._cache.get(_SSTHRESH_KEY)
        return float(raw) if raw else settings.throttle_min_delay

    async def _apply_403_penalty(self) -> None:
        current_delay = await self.get_current_delay()
        new_ssthresh = min(current_delay * 2, settings.throttle_max_delay)
        new_delay = min(
            max(current_delay * 2, settings.throttle_penalty_delay),
            settings.throttle_max_delay,
        )
        await self._cache.set(_DELAY_KEY, str(new_delay).encode())
        await self._cache.set(_SSTHRESH_KEY, str(new_ssthresh).encode())
        await self._cache.set(_LAST_403_KEY, str(time.time()).encode())
        await self._cache.set(_STREAK_KEY, b"0")
        self._penalty_start = time.monotonic()

        if settings.prometheus_enabled:
            throttle_current_delay_seconds.set(new_delay)
            throttle_403_total.inc()
            blizzard_rate_limited_total.inc()

        logger.warning(
            "[Throttle] Blizzard 403 — delay {:.2f}s → {:.2f}s (penalty {}s)",
            current_delay,
            new_delay,
            settings.throttle_penalty_duration,
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

    async def _on_success(self) -> None:
        raw_streak = await self._cache.get(_STREAK_KEY)
        streak = int(raw_streak) if raw_streak else 0
        streak += 1

        current_delay = await self.get_current_delay()
        ssthresh = await self._get_ssthresh()

        new_delay: float | None = None

        if current_delay > ssthresh:
            # Slow Start phase: halve delay every N successes
            if streak >= settings.throttle_slow_start_n_successes:
                new_delay = current_delay / 2
                streak = 0
        # AIMD phase: decrease delay by delta every M successes
        elif streak >= settings.throttle_aimd_n_successes:
            new_delay = current_delay - settings.throttle_aimd_delta
            streak = 0

        await self._cache.set(_STREAK_KEY, str(streak).encode())

        if new_delay is not None:
            new_delay = max(
                settings.throttle_min_delay,
                min(new_delay, settings.throttle_max_delay),
            )
            await self._cache.set(_DELAY_KEY, str(new_delay).encode())

            if settings.prometheus_enabled:
                throttle_current_delay_seconds.set(new_delay)

            logger.debug(
                "[Throttle] {}: {:.3f}s → {:.3f}s (streak reset)",
                "Slow Start" if current_delay > ssthresh else "AIMD",
                current_delay,
                new_delay,
            )
