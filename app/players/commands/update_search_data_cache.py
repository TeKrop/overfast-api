"""Command used in order to retrieve the last version of the namecards"""

import json
import re

import httpx

from app.cache_manager import CacheManager
from app.config import settings
from app.enums import Locale
from app.helpers import send_discord_webhook_message
from app.overfast_logger import logger

from ..enums import SearchDataType
from ..exceptions import SearchDataRetrievalError

# Generic cache manager used in the process
cache_manager = CacheManager()

# Mapping between the search data type and the variable name in JS
variable_name_mapping: dict[SearchDataType, str | None] = {
    SearchDataType.PORTRAIT: "avatars",
    SearchDataType.NAMECARD: "namecards",
    SearchDataType.TITLE: "titles",
}


def get_search_page() -> httpx.Response:
    try:
        response = httpx.get(
            f"{settings.blizzard_host}/{Locale.ENGLISH_US}{settings.search_data_path}"
        )
    except httpx.RequestError as error:
        logger.exception("An error occurred while requesting search data !")
        raise SearchDataRetrievalError from error
    else:
        return response


def extract_search_data(html_content: str, data_type: SearchDataType) -> dict | None:
    variable_name = variable_name_mapping[data_type]
    if not variable_name:
        return None

    data_regexp = rf"const {variable_name} = (\{{.*\}})\n"

    result = re.search(data_regexp, html_content)

    if not result:
        error_message = f"{data_type} data not found on Blizzard page !"
        logger.exception(error_message)
        send_discord_webhook_message(error_message)
        raise SearchDataRetrievalError

    try:
        json_result = json.loads(result[1])
    except ValueError as error:
        error_message = f"Invalid format for {data_type} data on Blizzard page !"
        logger.exception(error_message)
        send_discord_webhook_message(error_message)
        raise SearchDataRetrievalError from error
    else:
        return json_result


def transform_search_data(
    search_data: dict, data_type: SearchDataType
) -> dict[str, str]:
    def get_data_type_value(data_value: dict) -> str:
        match data_type:
            case SearchDataType.PORTRAIT | SearchDataType.NAMECARD:
                return data_value["icon"]

            case SearchDataType.TITLE:
                return data_value["name"]["en_US"]

    return {
        data_key: get_data_type_value(data_value)
        for data_key, data_value in search_data.items()
    }


def retrieve_search_data(
    data_type: SearchDataType, search_page: httpx.Response
) -> dict[str, str]:
    logger.info("Extracting {} data from HTML data...", data_type)
    search_data = extract_search_data(search_page.text, data_type)

    logger.info("Transforming data...")
    return transform_search_data(search_data, data_type)


def update_search_data_cache():
    """Main method of the script"""
    try:
        logger.info("Retrieving Blizzard search page...")
        search_page = get_search_page()

        logger.info("Retrieving search data...")
        search_data = {
            data_type: retrieve_search_data(data_type, search_page)
            for data_type in SearchDataType
            if data_type in variable_name_mapping
        }
    except SearchDataRetrievalError as error:
        raise SystemExit from error

    logger.info("Saving search data...")
    cache_manager.update_search_data_cache(search_data)


def main():
    """Main method of the script"""
    update_search_data_cache()


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="update_search_data_cache"))
    main()
