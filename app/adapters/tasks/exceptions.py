"""Exceptions specific to the background task adapter layer."""


class BlizzardTimeoutError(Exception):
    """Raised by the worker when a Blizzard request times out (HTTP 504).

    Used as a precise filter for the taskiq retry middleware so that only
    genuine Blizzard timeouts are retried, not other HTTP errors (404, 503…).
    """

    def __str__(self) -> str:
        return "Blizzard request timed out"
