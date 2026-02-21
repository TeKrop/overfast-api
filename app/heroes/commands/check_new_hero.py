"""Command used in order to check if a new hero is in the heroes list, compared
to the internal heroes list. If this is a case, a Discord notification is sent to the
developer.
"""

import asyncio

from fastapi import HTTPException

from app.adapters.blizzard.parsers.heroes import fetch_heroes_html, parse_heroes_html
from app.config import settings
from app.exceptions import ParserParsingError
from app.helpers import send_discord_webhook_message
from app.overfast_client import OverFastClient
from app.overfast_logger import logger

from ..enums import HeroKey


async def get_distant_hero_keys(client: OverFastClient) -> set[str]:
    """Get a set of Overwatch hero keys from the Blizzard heroes page"""
    try:
        html = await fetch_heroes_html(client)
        heroes = parse_heroes_html(html)
    except (HTTPException, ParserParsingError) as error:
        raise SystemExit from error

    return {hero["key"] for hero in heroes}


def get_local_hero_keys() -> set[str]:
    """Get a set of Overwatch hero keys from the local HeroKey enum"""
    return set(HeroKey)


async def main():
    """Main method of the script"""
    logger.info("Checking if a Discord webhook is configured...")
    if not settings.discord_webhook_enabled:
        logger.info("No Discord webhook configured ! Exiting...")
        raise SystemExit

    logger.info("OK ! Starting to check if a new hero is here...")

    client = OverFastClient()

    distant_hero_keys = await get_distant_hero_keys(client)
    local_hero_keys = get_local_hero_keys()

    await client.aclose()

    new_hero_keys = distant_hero_keys - local_hero_keys
    if len(new_hero_keys) > 0:
        logger.info("New hero keys were found : {}", new_hero_keys)
        send_discord_webhook_message(
            title="🎮 New Heroes Detected",
            description="New Overwatch heroes have been released!",
            fields=[
                {
                    "name": "Hero Keys",
                    "value": f"`{', '.join(sorted(new_hero_keys))}`",
                    "inline": False,
                },
                {
                    "name": "Action Required",
                    "value": "Please add these keys to the `HeroKey` enum configuration.",
                    "inline": False,
                },
            ],
            color=0x2ECC71,
        )
    else:
        logger.info("No new hero found. Exiting.")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="check_new_hero"))
    asyncio.run(main())
