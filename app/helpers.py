"""Parser Helpers module"""

import csv
import traceback
from functools import cache
from pathlib import Path

import httpx
from fastapi import HTTPException, status

from .config import settings
from .decorators import rate_limited
from .models import (
    BlizzardErrorMessage,
    InternalServerErrorMessage,
    RateLimitErrorMessage,
)
from .overfast_logger import logger

# Typical routes responses to return
success_responses = {
    status.HTTP_200_OK: {
        "description": "Successful Response",
        "headers": {
            settings.cache_ttl_header: {
                "description": "The TTL value for the cached response, in seconds",
                "schema": {
                    "type": "string",
                    "example": "600",
                },
            },
        },
    },
}

routes_responses = {
    **success_responses,
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": RateLimitErrorMessage,
        "description": "Rate Limit Error",
        "headers": {
            settings.retry_after_header: {
                "description": "Indicates how long to wait before making a new request",
                "schema": {
                    "type": "string",
                    "example": "5",
                },
            }
        },
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": InternalServerErrorMessage,
        "description": "Internal Server Error",
    },
    status.HTTP_504_GATEWAY_TIMEOUT: {
        "model": BlizzardErrorMessage,
        "description": "Blizzard Server Error",
    },
}


def overfast_internal_error(url: str, error: Exception) -> HTTPException:
    """Returns an Internal Server Error. Also log it and eventually send
    a Discord notification via a webhook if configured.
    """

    # Log the critical error
    logger.critical(
        "Internal server error for URL {} : {}\n{}",
        url,
        str(error),
        traceback.format_stack(),
    )

    # If we're using a profiler, it means we're debugging, raise the error
    # directly in order to have proper backtrace in logs
    if settings.profiler:
        raise error  # pragma: no cover

    # Else, send a message to the given channel using Discord Webhook URL
    send_discord_webhook_message(
        f"* **URL** : {url}\n"
        f"* **Error type** : {type(error).__name__}\n"
        f"* **Message** : {error}",
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=settings.internal_server_error_message,
    )


@rate_limited(max_calls=1, interval=1800)
def send_discord_webhook_message(message: str) -> httpx.Response | None:
    """Helper method for sending a Discord webhook message. It's limited to
    one call per 30 minutes with the same parameters."""
    if not settings.discord_webhook_enabled:
        logger.error(message)
        return None

    return httpx.post(  # pragma: no cover
        settings.discord_webhook_url, data={"content": message}, timeout=10
    )


@cache
def read_csv_data_file(filename: str) -> list[dict[str, str]]:
    """Helper method for obtaining CSV DictReader from a path"""
    with Path(f"{Path.cwd()}/app/{filename}/data/{filename}.csv").open(
        encoding="utf-8"
    ) as csv_file:
        return list(csv.DictReader(csv_file, delimiter=","))


@cache
def get_human_readable_duration(duration: int) -> str:
    # Define the time units
    days, remainder = divmod(duration, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    # Build the human-readable string
    duration_parts = []
    if days > 0:
        duration_parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        duration_parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        duration_parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")

    return ", ".join(duration_parts)
