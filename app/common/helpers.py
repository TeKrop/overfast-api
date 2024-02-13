"""Parser Helpers module"""
import csv
import json
import zlib
from functools import cache
from pathlib import Path
from random import randint
from typing import TYPE_CHECKING, Any

import httpx
from fastapi import HTTPException, Request, status

from app.config import settings
from app.models.errors import BlizzardErrorMessage, InternalServerErrorMessage

from .decorators import rate_limited
from .logging import logger

if TYPE_CHECKING:  # pragma: no cover
    from app.common.enums import HeroKey


# Typical routes responses to return
routes_responses = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": InternalServerErrorMessage,
        "description": "Internal Server Error",
    },
    status.HTTP_504_GATEWAY_TIMEOUT: {
        "model": BlizzardErrorMessage,
        "description": "Blizzard Server Error",
    },
}

# List of players used for testing
players_ids = [
    "copypasting-1216",  # Player with an empty hero career stats (lucio)
    "Dekk-2677",  # Classic profile without rank
    "KIRIKO-21253",  # Profile with rank on only two roles
    "Player-1112937",  # Console player
    "quibble-11594",  # Profile without endorsement
    "TeKrop-2217",  # Classic profile
    "Unknown-1234",  # No player
    "JohnV1-1190",  # Player without any title ingame
]

# httpx client settings
overfast_client_settings = {
    "headers": {
        "User-Agent": (
            f"OverFastAPI v{settings.app_version} - "
            "https://github.com/TeKrop/overfast-api"
        ),
        "From": "valentin.porchet@proton.me",
    },
    "http2": True,
    "timeout": 10,
    "follow_redirects": True,
}

# Instanciate global httpx client
overfast_client = httpx.AsyncClient(**overfast_client_settings)


async def overfast_request(url: str) -> httpx.Response:
    """Make an HTTP GET request with custom headers and retrieve the result"""
    try:
        logger.debug("Requesting {}...", url)
        response = await overfast_client.get(url)
    except httpx.TimeoutException as error:
        raise blizzard_response_error(
            status_code=0,
            error="Blizzard took more than 10 seconds to respond, resulting in a timeout",
        ) from error
    else:
        logger.debug("OverFast request done !")
        return response


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


def blizzard_response_error(status_code: int, error: str) -> HTTPException:
    """Retrieve a generic error response when a Blizzard page doesn't load"""
    logger.error(
        "Received an error from Blizzard. HTTP {} : {}",
        status_code,
        error,
    )

    return HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        detail=f"Couldn't get Blizzard page (HTTP {status_code} error) : {error}",
    )


def blizzard_response_error_from_request(req: Request) -> HTTPException:
    """Alias for sending Blizzard error from a request directly"""
    return blizzard_response_error(req.status_code, req.text)


@rate_limited(max_calls=1, interval=1800)
def send_discord_webhook_message(message: str) -> httpx.Response | None:
    """Helper method for sending a Discord webhook message. It's limited to
    one call per 30 minutes with the same parameters."""
    return (
        httpx.post(settings.discord_webhook_url, data={"content": message}, timeout=10)
        if settings.discord_webhook_enabled
        else None
    )


def read_html_file(filepath: str) -> str | None:
    """Helper method for retrieving fixture HTML file data"""
    html_file_object = Path(f"{settings.test_fixtures_root_path}/html/{filepath}")
    if not html_file_object.is_file():
        return None  # pragma: no cover

    with html_file_object.open(encoding="utf-8") as html_file:
        return html_file.read()


def read_json_file(filepath: str) -> dict | list | None:
    """Helper method for retrieving fixture JSON file data"""
    with Path(f"{settings.test_fixtures_root_path}/json/{filepath}").open(
        encoding="utf-8",
    ) as json_file:
        return json.load(json_file)


@cache
def read_csv_data_file(filepath: str) -> list[dict[str, str]]:
    """Helper method for obtaining CSV DictReader from a path"""
    with Path(f"{Path.cwd()}/app/data/{filepath}").open(encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file, delimiter=","))


def compress_json_value(value: dict | list) -> str:
    """Helper method to transform a value into compressed JSON data"""
    return zlib.compress(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def decompress_json_value(value: str) -> dict | list:
    """Helper method to retrieve a value from a compressed JSON data"""
    return json.loads(zlib.decompress(value).decode("utf-8"))


def get_spread_value(value: int, spread_percentage: float) -> int:
    """Helper method to get a random value from a specific range
    by using a percentage of the value, from (value - %*value) to (value + %*value)
    """
    min_percentage = (100 - spread_percentage) / 100
    max_percentage = (100 + spread_percentage) / 100
    return randint(int(min_percentage * value), int(max_percentage * value))


@cache
def get_hero_name(hero_key: "HeroKey") -> str:
    """Get a hero name based on the CSV file"""
    heroes_data = read_csv_data_file("heroes.csv")
    return next(
        (
            hero_data["name"]
            for hero_data in heroes_data
            if hero_data["key"] == hero_key
        ),
        hero_key,
    )


def dict_insert_value_before_key(
    data: dict,
    key: str,
    new_key: str,
    new_value: Any,
) -> dict:
    """Insert a given key/value pair before another key in a given dict"""
    if key not in data:
        raise KeyError

    # Retrieve the key position
    key_pos = list(data.keys()).index(key)

    # Retrieve dict items as a list of tuples
    data_items = list(data.items())

    # Insert the new tuple in the given position
    data_items.insert(key_pos, (new_key, new_value))

    # Convert back the list into a dict and return it
    return dict(data_items)


def key_to_label(key: str) -> str:
    """Transform a given key in lowercase format into a human format"""
    return " ".join(s.capitalize() for s in key.split("_"))


@cache
def get_player_title(title: str | None) -> str | None:
    """Get player title from string extracted from Blizzard page. This is
    where we're handling the special "no title" case for which we return None
    """
    return None if title and title.lower() == "no title" else title
