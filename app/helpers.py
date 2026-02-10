"""Parser Helpers module"""

import csv
import traceback
from datetime import UTC, datetime
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

    # Get error details
    error_str = str(error)
    error_type = type(error).__name__

    # Log the critical error with full traceback
    logger.critical(
        "Internal server error for URL {} : {}\n{}",
        url,
        error_str,
        traceback.format_exc(),
    )

    # If we're using a profiler, it means we're debugging, raise the error
    # directly in order to have proper backtrace in logs
    if settings.profiler:
        raise error  # pragma: no cover

    # Truncate error message for Discord (keep first part which is most relevant)
    max_error_length = 900  # Field value limit is 1024, leave room for formatting
    if len(error_str) > max_error_length:
        # For validation errors, try to show just the summary
        if "validation error" in error_str.lower():
            lines = error_str.split("\n")
            error_str = "\n".join(
                lines[:5]
            )  # First 5 lines usually contain the key info
            if len(error_str) > max_error_length:
                error_str = error_str[:max_error_length]
        else:
            error_str = error_str[:max_error_length]

    # Send a message to the given channel using Discord Webhook URL
    send_discord_webhook_message(
        title="🚨 Internal Server Error",
        url=f"{settings.app_base_url}{url}" if not url.startswith("http") else url,
        fields=[
            {"name": "Error Type", "value": f"`{error_type}`", "inline": True},
            {"name": "Endpoint", "value": f"`{url}`", "inline": True},
            {
                "name": "Error Message",
                "value": f"```\n{error_str}\n```",
                "inline": False,
            },
        ],
        color=0xE74C3C,  # Red
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=settings.internal_server_error_message,
    )


def _truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def _truncate_embed_fields(
    fields: list[dict[str, str | bool]],
) -> list[dict[str, str | bool]]:
    """Truncate field names and values to Discord limits."""
    max_field_name_length = 250  # Actual limit: 256
    max_field_value_length = 1000  # Actual limit: 1024

    for field in fields:
        name = field.get("name", "")
        value = field.get("value", "")

        if isinstance(name, str) and len(name) > max_field_name_length:
            field["name"] = _truncate_text(name, max_field_name_length)
        if isinstance(value, str) and len(value) > max_field_value_length:
            field["value"] = _truncate_text(
                value, max_field_value_length, "\n*(truncated)*"
            )

    return fields


@rate_limited(max_calls=1, interval=1800)
def send_discord_webhook_message(
    *,
    title: str | None = None,
    description: str | None = None,
    url: str | None = None,
    fields: list[dict[str, str | bool]] | None = None,
    color: int | None = None,
) -> httpx.Response | None:
    """Helper method for sending a Discord webhook message using modern embed syntax.
    It's limited to one call per 30 minutes with the same parameters.

    Args:
        title: Optional title for the embed (max 256 chars)
        description: Optional description text (max 4096 chars)
        url: Optional URL to make the title clickable
        fields: Optional list of field dicts with 'name', 'value', and optional 'inline' keys
        color: Optional color for the embed (decimal format, e.g., 0xFF0000 for red)
    """
    if not settings.discord_webhook_enabled:
        logger.error(f"{title}: {description}")
        return None

    # Apply Discord embed length limits
    if title:
        title = _truncate_text(title, 250)
    if description:
        description = _truncate_text(description, 4000, "\n\n*(truncated)*")
    if fields:
        fields = _truncate_embed_fields(fields)

    # Build the embed payload
    embed = {
        "color": color or 0xE74C3C,  # Default to red for errors/alerts
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if title:
        embed["title"] = title
    if description:
        embed["description"] = description
    if url:
        embed["url"] = url
    if fields:
        embed["fields"] = fields

    payload = {"username": "OverFast API", "embeds": [embed]}

    return httpx.post(  # pragma: no cover
        settings.discord_webhook_url, json=payload, timeout=10
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
