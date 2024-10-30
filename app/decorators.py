"""Decorators module"""

import time
from collections.abc import Callable
from functools import wraps

from .logging import logger


def rate_limited(max_calls: int, interval: int):
    """Put a rate limit on function call using specified parameters :
    X **max_calls** per *interval* seconds. It prevents too many calls of a
    given method with the exact same parameters, for example the Discord
    webhook if there is a critical parsing error.
    """

    def decorator(func: Callable):
        call_history = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Define a unique key by using given parameters
            key = (args, tuple(kwargs.items()))
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
                    func.__name__,
                )
                return None

        return wrapper

    return decorator
