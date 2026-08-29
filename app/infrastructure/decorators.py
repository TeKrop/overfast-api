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
            cutoff = now - interval

            # Expire whole keys, not just the timestamps inside them. The key
            # embeds the call arguments, and the only caller passes the error
            # text in `fields`, so without dropping empty keys every distinct
            # traceback leaks an entry for the lifetime of the process — on
            # the error path, where volume spikes.
            for seen_key in list(call_history):
                kept = [t for t in call_history[seen_key] if t >= cutoff]
                if kept:
                    call_history[seen_key] = kept
                else:
                    del call_history[seen_key]

            timestamps = call_history.setdefault(key, [])
            if len(timestamps) < max_calls:
                timestamps.append(now)
                return func(*args, **kwargs)

            logger.warning(
                "Rate limit exceeded for {} with the same parameters. Try again later.",
                func.__name__,  # ty: ignore[unresolved-attribute]
            )
            return None

        return wrapper

    return decorator
