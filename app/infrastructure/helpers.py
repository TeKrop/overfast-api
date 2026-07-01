"""Infrastructure helpers — error reporting and Discord notifications."""

import traceback
from datetime import UTC, datetime
from typing import Any

import httpx2
from fastapi import HTTPException, status

from app.config import settings
from app.infrastructure.decorators import rate_limited
from app.infrastructure.logger import logger


def overfast_internal_error(url: str, error: Exception) -> HTTPException:
    """Return an Internal Server Error HTTPException.

    Also logs the error at CRITICAL level and optionally sends a Discord
    notification via webhook.  Called from domain services and the API
    exception handler for unexpected parsing failures.
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


_TITLE_SUFFIX = "..."
_DESC_SUFFIX = "\n\n*(truncated)*"
_FIELD_SUFFIX = "\n*(truncated)*"

_MAX_TITLE_LEN = 250
_MAX_DESC_LEN = 4000
_MAX_FIELD_NAME_LEN = 250
_MAX_FIELD_VALUE_LEN = 1000


def _truncate_embed_content(
    title: str | None,
    description: str | None,
    fields: list[dict[str, Any]] | None,
) -> tuple[str | None, str | None, list[dict[str, Any]] | None]:
    """Enforce Discord embed length limits, truncating with a visible suffix."""
    if title and len(title) > _MAX_TITLE_LEN:
        title = title[: _MAX_TITLE_LEN - len(_TITLE_SUFFIX)] + _TITLE_SUFFIX
    if description and len(description) > _MAX_DESC_LEN:
        description = description[: _MAX_DESC_LEN - len(_DESC_SUFFIX)] + _DESC_SUFFIX
    if fields:
        for f in fields:
            name, value = f.get("name", ""), f.get("value", "")
            if isinstance(name, str) and len(name) > _MAX_FIELD_NAME_LEN:
                f["name"] = (
                    name[: _MAX_FIELD_NAME_LEN - len(_TITLE_SUFFIX)] + _TITLE_SUFFIX
                )
            if isinstance(value, str) and len(value) > _MAX_FIELD_VALUE_LEN:
                f["value"] = (
                    value[: _MAX_FIELD_VALUE_LEN - len(_FIELD_SUFFIX)] + _FIELD_SUFFIX
                )
    return title, description, fields


def _build_embed(
    title: str | None,
    description: str | None,
    url: str | None,
    fields: list[dict[str, Any]] | None,
    color: int | None,
) -> dict[str, Any]:
    embed: dict[str, Any] = {
        "color": color or 0xE74C3C,
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
    return embed


@rate_limited(max_calls=1, interval=1800)
def send_discord_webhook_message(
    *,
    title: str | None = None,
    description: str | None = None,
    url: str | None = None,
    fields: list[dict[str, Any]] | None = None,
    color: int | None = None,
) -> httpx2.Response | None:
    """Send a Discord webhook message using modern embed syntax.

    Rate-limited to one call per 30 minutes with the same parameters.

    Args:
        title: Optional title for the embed (max 256 chars)
        description: Optional description text (max 4096 chars)
        url: Optional URL to make the title clickable
        fields: Optional list of field dicts with 'name', 'value', and optional 'inline' keys
        color: Optional color for the embed (decimal format, e.g., 0xFF0000 for red)
    """
    if not settings.discord_webhook_enabled:
        logger.error("{}: {}", title, description)
        return None

    title, description, fields = _truncate_embed_content(title, description, fields)
    embed = _build_embed(title, description, url, fields, color)
    payload = {"username": "OverFast API", "embeds": [embed]}

    return httpx2.post(  # pragma: no cover
        settings.discord_webhook_url, json=payload, timeout=10
    )
