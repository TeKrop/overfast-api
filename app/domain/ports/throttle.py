"""Throttle port protocol for dependency injection"""

from typing import Protocol


class ThrottlePort(Protocol):
    """Protocol for adaptive request throttling."""

    async def wait_before_request(self) -> None:
        """Sleep for the current throttle delay, or raise RateLimitedError if in penalty."""
        ...

    async def adjust_delay(self, latency: float, status_code: int) -> None:
        """Update the throttle delay based on the observed response."""
        ...

    async def is_rate_limited(self) -> int:
        """Return remaining penalty seconds; 0 if not currently rate-limited."""
        ...

    async def get_current_delay(self) -> float:
        """Return the current inter-request delay (seconds)."""
        ...
