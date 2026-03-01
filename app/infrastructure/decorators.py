"""Decorators module"""

import time
from functools import wraps
from typing import TYPE_CHECKING

from app.infrastructure.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable


def rate_limited(max_calls: int, interval: int):
    """Put a rate limit on function call using specified parameters :
    X **max_calls** per *interval* seconds. It prevents too many calls of a
    given method with the exact same parameters, for example the Discord
    webhook if there is a critical parsing error.
    """

    def _make_hashable(obj):
        """Convert unhashable types to hashable equivalents"""
        if isinstance(obj, dict):
            return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
        if isinstance(obj, list):
            return tuple(_make_hashable(item) for item in obj)
        return obj

    def decorator(func: Callable) -> Callable:
        call_history = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Define a unique key by using given parameters
            # Convert unhashable types (list, dict) to hashable ones
            hashable_args = tuple(_make_hashable(arg) for arg in args)
            hashable_kwargs = tuple(
                sorted((k, _make_hashable(v)) for k, v in kwargs.items())
            )
            key = (hashable_args, hashable_kwargs)
            now = time.time()

            # If the key is not already in history, insert it and make the call
            if key not in call_history:
                call_history[key] = [now]
                return func(*args, **kwargs)

            # Else, update the call history by removing expired limits
            timestamps = call_history[key]
            timestamps[:] = [t for t in timestamps if t >= now - interval]

            # If there is no limit anymore or if the max
            # number of calls hasn't been reached yet, continue
            if len(timestamps) < max_calls:
                timestamps.append(now)
                return func(*args, **kwargs)
            else:
                # Else the function is being rate limited
                logger.warning(
                    "Rate limit exceeded for {} with the same "
                    "parameters. Try again later.",
                    func.__name__,  # ty: ignore[unresolved-attribute]
                )
                return None

        return wrapper

    return decorator
