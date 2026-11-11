"""Decorators module"""

import time
from functools import wraps
from typing import TYPE_CHECKING, Any

from app.infrastructure.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable


def _make_hashable(obj: object) -> object:
    """Convert unhashable types to hashable equivalents"""
    if isinstance(obj, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_make_hashable(item) for item in obj)
    return obj


def _make_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...]:
    """Build a unique hashable key from call parameters"""
    return (
        tuple(_make_hashable(arg) for arg in args),
        tuple(sorted((k, _make_hashable(v)) for k, v in kwargs.items())),
    )


def _is_allowed(
    call_history: dict[Any, list[float]], key: object, max_calls: int, interval: int
) -> bool:
    """Record the call and return True unless the rate limit is exceeded"""
    now = time.time()
    timestamps = call_history.setdefault(key, [])
    # Drop expired calls
    timestamps[:] = [t for t in timestamps if t >= now - interval]
    if len(timestamps) >= max_calls:
        return False
    timestamps.append(now)
    return True


def rate_limited[**P, R](
    max_calls: int, interval: int
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Put a rate limit on function call using specified parameters :
    X **max_calls** per *interval* seconds. It prevents too many calls of a
    given method with the exact same parameters, for example the Discord
    webhook if there is a critical parsing error.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        call_history: dict[Any, list[float]] = {}

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            if _is_allowed(call_history, _make_key(args, kwargs), max_calls, interval):
                return func(*args, **kwargs)
            logger.warning(
                "Rate limit exceeded for {} with the same parameters. Try again later.",
                func.__name__,
            )
            return None

        return wrapper

    return decorator
