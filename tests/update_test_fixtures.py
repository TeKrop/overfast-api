"""Update Parsers Test Fixtures module
Using Blizzard real data about heroes, some players and maps,
download and update parsers test HTML fixtures
"""

import argparse
import asyncio
from pathlib import Path

import httpx
from fastapi import status

from app.config import settings
from app.enums import Locale
from app.overfast_logger import logger
from app.players.enums import HeroKey
from tests.helpers import players_ids, unknown_player_id


def parse_parameters() -> argparse.Namespace:  # pragma: no cover
    """Parse command line arguments and returns the corresponding Namespace object"""
    parser = argparse.ArgumentParser(
        description=(
            "Update test data fixtures by retrieving Blizzard pages directly. "
            "By default, all the tests data will be updated."
        ),
    )
    parser.add_argument(
        "-He",
        "--heroes",
        action="store_true",
        default=False,
        help="update heroes test data",
    )
    parser.add_argument(
        "-Ho",
        "--home",
        action="store_true",
        default=False,
        help="update home test data (roles, gamemodes)",
    )
    parser.add_argument(
        "-P",
        "--players",
        action="store_true",
        default=False,
        help="update players test data",
    )

    args = parser.parse_args()

    # If no value was given by the user, all is true
    if not any(vars(args).values()):
        args.heroes = True
        args.home = True
        args.players = True

    return args


def list_routes_to_update(args: argparse.Namespace) -> dict[str, str]:
    """Method used to construct the dict of routes to update. The result
    is dictionnary, mapping the blizzard route path to the local filepath."""
    route_file_mapping = {}

    if args.heroes:
        logger.info("Adding heroes routes...")

        route_file_mapping |= {
            f"{settings.heroes_path}/": "/heroes.html",
            **{
                f"{settings.heroes_path}/{hero}/": f"/heroes/{hero}.html"
                for hero in HeroKey
            },
        }

    if args.players:
        logger.info("Adding player careers routes...")
        route_file_mapping.update(
            **{
                f"{settings.career_path}/{player_id}/": f"/players/{player_id}.html"
                for player_id in [*players_ids, unknown_player_id]
            },
        )

    if args.home:
        logger.info("Adding home routes...")
        route_file_mapping[settings.home_path] = "/home.html"

    return route_file_mapping


def save_fixture_file(filepath: str, content: str):  # pragma: no cover
    """Method used to save the fixture file on the disk"""
    with Path(filepath).open(mode="w", encoding="utf-8") as html_file:
        html_file.write(content)
        html_file.close()
        logger.info("File saved !")


async def main():
    """Main method of the script"""
    logger.info("Updating test fixtures...")

    args = parse_parameters()
    logger.debug("args : {}", args)

    # Initialize data
    route_file_mapping = list_routes_to_update(args)
    locale = Locale.ENGLISH_US

    # Do the job
    test_data_path = f"{settings.test_fixtures_root_path}/html"
    async with httpx.AsyncClient() as client:
        for route, filepath in route_file_mapping.items():
            logger.info("Updating {}{}...", test_data_path, filepath)
            logger.info("GET {}/{}{}...", settings.blizzard_host, locale, route)
            response = await client.get(
                f"{settings.blizzard_host}/{locale}{route}",
                headers={"Accept": "text/html"},
                follow_redirects=True,
            )
            logger.debug(
                "HTTP {} / Time : {}",
                response.status_code,
                response.elapsed.total_seconds(),
            )
            if response.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}:
                save_fixture_file(f"{test_data_path}{filepath}", response.text)
            else:
                logger.error("Error while getting the page : {}", response.text)

    logger.info("Fixtures update finished !")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="update_test_fixtures"))
    asyncio.run(main())
