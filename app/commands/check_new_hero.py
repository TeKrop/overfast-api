"""Command used in order to check if a new hero is in the heroes list, compared
to the internal heroes list. If this is a case, a Discord notification is sent to the
developer.
"""
import asyncio

from fastapi import HTTPException

from app.common.enums import HeroKey
from app.common.helpers import send_discord_webhook_message
from app.common.logging import logger
from app.config import settings
from app.parsers.heroes_parser import HeroesParser


def get_distant_hero_keys() -> set[str]:
    """Get a set of Overwatch hero keys from the Blizzard heroes page"""
    heroes_parser = HeroesParser()

    try:
        asyncio.run(heroes_parser.retrieve_and_parse_data())
    except HTTPException as error:
        raise SystemExit from error

    return {hero["key"] for hero in heroes_parser.data}


def get_local_hero_keys() -> set[str]:
    """Get a set of Overwatch hero keys from the local HeroKey enum"""
    return {h.value for h in HeroKey}


def main():
    """Main method of the script"""
    logger.info("Checking if a Discord webhook is configured...")
    if not settings.discord_webhook_enabled:
        logger.info("No Discord webhook configured ! Exiting...")
        raise SystemExit

    logger.info("OK ! Starting to check if a new hero is here...")
    distant_hero_keys = get_distant_hero_keys()
    local_hero_keys = get_local_hero_keys()

    # Compare both sets. If we have a difference, notify the developer
    new_hero_keys = distant_hero_keys - local_hero_keys
    if len(new_hero_keys) > 0:
        logger.info("New hero keys were found : {}", new_hero_keys)
        send_discord_webhook_message(
            "New Overwatch heroes detected, please add the following "
            f"keys into the configuration : {new_hero_keys}"
        )
    else:
        logger.info("No new hero found. Exiting.")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="check_new_hero"))
    main()
