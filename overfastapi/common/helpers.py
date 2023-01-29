"""Parser Helpers module"""
import csv
import json
from pathlib import Path

import requests
from fastapi import HTTPException, Request, status

from overfastapi.common.logging import logger
from overfastapi.config import (
    DISCORD_WEBHOOK_ENABLED,
    DISCORD_WEBHOOK_URL,
    OVERFAST_API_VERSION,
    TEST_FIXTURES_ROOT_PATH,
)
from overfastapi.models.errors import BlizzardErrorMessage, InternalServerErrorMessage

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
    "Player-137712",  # Private profile
    "TeKrop-2217",  # Classic profile
    "Unknown-1234",  # No player
]


def overfast_request(url: str) -> requests.Response:
    """Make an HTTP GET request with custom headers and retrieve the result"""
    headers = {
        "User-Agent": (
            f"OverFastAPI v{OVERFAST_API_VERSION} - "
            "https://github.com/TeKrop/overfast-api"
        ),
        "From": "vporchet@gmail.com",
    }
    try:
        return requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.Timeout as error:
        raise blizzard_response_error(
            status_code=0,
            error="Blizzard took more than 10 seconds to respond, resulting in a timeout",
        ) from error


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
        f"* **Message** : {error}"
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
        detail=(f"Couldn't get Blizzard page (HTTP {status_code} error) : {error}"),
    )


def blizzard_response_error_from_request(req: Request) -> HTTPException:
    """Alias for sending Blizzard error from a request directly"""
    return blizzard_response_error(req.status_code, req.text)


def send_discord_webhook_message(message: str) -> requests.Response | None:
    """Helper method for sending a Discord webhook message"""
    return (
        requests.post(DISCORD_WEBHOOK_URL, data={"content": message}, timeout=10)
        if DISCORD_WEBHOOK_ENABLED
        else None
    )


def read_html_file(filepath: str) -> str:
    """Helper method for retrieving fixture HTML file data"""
    with open(
        f"{TEST_FIXTURES_ROOT_PATH}/html/{filepath}", encoding="utf-8"
    ) as html_file:
        return html_file.read()


def read_json_file(filepath: str) -> dict | list:
    """Helper method for retrieving fixture JSON file data"""
    with open(
        f"{TEST_FIXTURES_ROOT_PATH}/json/{filepath}", encoding="utf-8"
    ) as json_file:
        return json.load(json_file)


def read_csv_data_file(filepath: str) -> csv.DictReader:
    with open(
        f"{Path.cwd()}/overfastapi/data/{filepath}", encoding="utf-8"
    ) as csv_file:
        yield from csv.DictReader(csv_file, delimiter=";")
