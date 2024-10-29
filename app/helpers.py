"""Parser Helpers module"""

import csv
from functools import cache
from pathlib import Path

import httpx
from fastapi import HTTPException, status

from .config import settings
from .decorators import rate_limited
from .logging import logger
from .models import (
    BlizzardErrorMessage,
    InternalServerErrorMessage,
    RateLimitErrorMessage,
)

# Typical routes responses to return
routes_responses = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": RateLimitErrorMessage,
        "description": "Rate Limit Error",
        "headers": {
            "Retry-After": {
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
        "Internal server error for URL {} : {}",
        url,
        str(error),
    )

    # If Discord Webhook configuration is enabled, send a message to the
    # given channel using Discord Webhook URL
    send_discord_webhook_message(
        f"* **URL** : {url}\n"
        f"* **Error type** : {type(error).__name__}\n"
        f"* **Message** : {error}",
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            "An internal server error occurred during the process. The developer "
            "received a notification, but don't hesitate to create a GitHub "
            "issue if you want any news concerning the bug resolution : "
            "https://github.com/TeKrop/overfast-api/issues"
        ),
    )


@rate_limited(max_calls=1, interval=1800)
def send_discord_webhook_message(message: str) -> httpx.Response | None:
    """Helper method for sending a Discord webhook message. It's limited to
    one call per 30 minutes with the same parameters."""
    return (
        httpx.post(settings.discord_webhook_url, data={"content": message}, timeout=10)
        if settings.discord_webhook_enabled
        else None
    )


@cache
def read_csv_data_file(filename: str) -> list[dict[str, str]]:
    """Helper method for obtaining CSV DictReader from a path"""
    with Path(f"{Path.cwd()}/app/{filename}/data/{filename}.csv").open(
        encoding="utf-8"
    ) as csv_file:
        return list(csv.DictReader(csv_file, delimiter=","))
