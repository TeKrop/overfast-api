"""Command used in order to retrieve the last version of the.
"""
import json
import re

import httpx

from app.common.cache_manager import CacheManager
from app.common.helpers import send_discord_webhook_message
from app.common.logging import logger
from app.config import settings

# Generic cache manager used in the process
cache_manager = CacheManager()


def extract_namecards_data(html_content: str) -> dict:
    result = re.search(r"const namecards = (\{.*\})\n", html_content)

    if not result:
        error_message = "Namecards not found on Blizzard page !"
        logger.exception(error_message)
        send_discord_webhook_message(error_message)
        raise SystemExit

    try:
        json_result = json.loads(result.group(1))
    except ValueError as error:
        error_message = "Invalid format for namecards on Blizzard page !"
        logger.exception(error_message)
        send_discord_webhook_message(error_message)
        raise SystemExit from error
    else:
        return json_result


def transform_namecards_data(namecards_data: dict) -> dict:
    return {
        namecard_key: namecard["icon"]
        for namecard_key, namecard in namecards_data.items()
    }


def main():
    """Main method of the script"""
    logger.info("Retrieving Blizzard search page...")
    try:
        response = httpx.get(f"{settings.blizzard_host}{settings.namecards_path}")
    except httpx.RequestError as error:
        logger.exception("An error occurred while requesting namecards !")
        raise SystemExit from error

    logger.info("Retrieving namecards from HTML data...")
    namecards_data = extract_namecards_data(response.text)

    logger.info("Transforming data...")
    namecards = transform_namecards_data(namecards_data)

    logger.info("Saving namecards...")
    cache_manager.update_namecards_cache(namecards)


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="update_namecards_cache"))
    main()
