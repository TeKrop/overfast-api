"""Command used in order to retrieve the last version of the namecards"""
import json
import re

import httpx

from app.common.cache_manager import CacheManager
from app.common.exceptions import NamecardsRetrievalError
from app.common.helpers import send_discord_webhook_message
from app.common.logging import logger
from app.config import settings

# Generic cache manager used in the process
cache_manager = CacheManager()


def get_search_page() -> httpx.Response:
    try:
        response = httpx.get(f"{settings.blizzard_host}{settings.namecards_path}")
    except httpx.RequestError as error:
        logger.exception("An error occurred while requesting namecards !")
        raise NamecardsRetrievalError from error
    else:
        return response


def extract_namecards_data(html_content: str) -> dict:
    result = re.search(r"const namecards = (\{.*\})\n", html_content)

    if not result:
        error_message = "Namecards not found on Blizzard page !"
        logger.exception(error_message)
        send_discord_webhook_message(error_message)
        raise NamecardsRetrievalError

    try:
        json_result = json.loads(result.group(1))
    except ValueError as error:
        error_message = "Invalid format for namecards on Blizzard page !"
        logger.exception(error_message)
        send_discord_webhook_message(error_message)
        raise NamecardsRetrievalError from error
    else:
        return json_result


def transform_namecards_data(namecards_data: dict) -> dict[str, str]:
    return {
        namecard_key: namecard["icon"]
        for namecard_key, namecard in namecards_data.items()
    }


def retrieve_namecards() -> dict[str, str]:
    logger.info("Retrieving Blizzard search page...")
    search_page = get_search_page()

    logger.info("Extracting namecards from HTML data...")
    namecards_data = extract_namecards_data(search_page.text)

    logger.info("Transforming data...")
    return transform_namecards_data(namecards_data)


def update_namecards_cache():
    """Main method of the script"""
    logger.info("Retrieving namecards...")

    try:
        namecards = retrieve_namecards()
    except NamecardsRetrievalError as error:
        raise SystemExit from error

    logger.info("Saving namecards...")
    cache_manager.update_namecards_cache(namecards)


def main():
    """Main method of the script"""
    update_namecards_cache()


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="update_namecards_cache"))
    main()
