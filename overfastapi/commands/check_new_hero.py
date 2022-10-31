"""Command used in order to check if a new hero is in the heroes list, compared
to the internal heroes list. If this is a case, a Discord notification is sent to the
developer.
"""
from overfastapi.common.enums import HeroKey
from overfastapi.common.helpers import overfast_request, send_discord_webhook_message
from overfastapi.common.logging import logger
from overfastapi.config import DISCORD_WEBHOOK_ENABLED
from overfastapi.handlers.list_heroes_request_handler import ListHeroesRequestHandler
from overfastapi.parsers.heroes_parser import HeroesParser


def get_distant_hero_keys() -> set[str]:
    """Get a set of Overwatch hero keys from the Blizzard heroes page"""

    heroes_url = ListHeroesRequestHandler().get_blizzard_url()
    req = overfast_request(heroes_url)
    if req.status_code != 200:
        logger.error(
            "Received an error from Blizzard. HTTP {} : {}",
            req.status_code,
            req.text,
        )
        raise SystemExit

    heroes_parser = HeroesParser(req.text)
    heroes_parser.parse()
    return {hero["key"] for hero in heroes_parser.data}


def get_local_hero_keys() -> set[str]:
    """Get a set of Overwatch hero keys from the local HeroKey enum"""
    return {h.value for h in HeroKey}


def main():
    """Main method of the script"""
    logger.info("Checking if a Discord webhook is configured...")
    if not DISCORD_WEBHOOK_ENABLED:
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
