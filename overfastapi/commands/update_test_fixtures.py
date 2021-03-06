"""Update Parsers Test Fixtures module
Using Blizzard real data about heroes, some players and maps,
download and update parsers test HTML fixtures
"""
import argparse

import requests

from overfastapi.common.enums import HeroKey
from overfastapi.common.logging import logger
from overfastapi.config import (
    BLIZZARD_HOST,
    CAREER_PATH,
    HEROES_PATH,
    MAPS_PATH,
    TEST_FIXTURES_ROOT_PATH,
)


def parse_parameters() -> argparse.Namespace:  # pragma: no cover
    """Parse command line arguments and returns the corresponding Namespace object"""
    parser = argparse.ArgumentParser(
        description=(
            "Update test data fixtures by retrieving Blizzard pages directly. "
            "By default, all the tests data will be updated."
        )
    )
    parser.add_argument(
        "-H",
        "--heroes",
        action="store_true",
        default=False,
        help="update heroes test data",
    )
    parser.add_argument(
        "-P",
        "--players",
        action="store_true",
        default=False,
        help="update players test data",
    )
    parser.add_argument(
        "-M",
        "--maps",
        action="store_true",
        default=False,
        help="update maps test data",
    )

    args = parser.parse_args()

    # If no value was given by the user, all is true
    if not any(vars(args).values()):
        args.heroes = True
        args.players = True
        args.maps = True

    return args


def list_routes_to_update(args: argparse.Namespace) -> dict[str, str]:
    """Method used to construct the dict of routes to update. The result
    is dictionnary, mapping the blizzard route path to the local filepath."""
    route_file_mapping = {}

    if args.heroes:
        logger.info("Adding heroes routes...")
        route_file_mapping.update(
            {
                HEROES_PATH: "/heroes.html",
                **{
                    f"{HEROES_PATH}/{hero.value}": f"/hero/{hero.value}.html"
                    for hero in HeroKey
                },
            }
        )

    if args.players:
        logger.info("Adding player careers routes...")
        players_list = (
            {"platform": "pc", "id": "TeKrop-2217"},
            {"platform": "pc", "id": "Player-162460"},
            {"platform": "pc", "id": "test-1337"},
            {"platform": "pc", "id": "Unknown-1234"},
            {
                "platform": "nintendo-switch",
                "id": "test-325d682072d7a4c61c33b6bbaa83b859",
            },
            {
                "platform": "nintendo-switch",
                "id": "test-e66c388f13a7f408a6e1738f3d5161e2",
            },
            {"platform": "xbl", "id": "xJaymog"},
            {"platform": "psn", "id": "Ka1zen_x"},
            {"platform": "psn", "id": "mightyy_Brig"},
        )
        route_file_mapping.update(
            **{
                f"{CAREER_PATH}/{player['platform']}/{player['id']}": f"/player/{player['id']}.html"
                for player in players_list
            }
        )

    if args.maps:
        logger.info("Adding maps routes...")
        route_file_mapping[MAPS_PATH] = "/maps.html"

    return route_file_mapping


def save_fixture_file(filepath: str, content: str):  # pragma: no cover
    """Method used to save the fixture file on the disk"""
    with open(filepath, "w", encoding="utf-8") as html_file:
        html_file.write(content)
        html_file.close()
        logger.info("File saved !")


def main():
    """Main method of the script"""
    logger.info("Updating test fixtures...")

    args = parse_parameters()
    logger.debug("args : {}", args)

    # Initialize data
    route_file_mapping = list_routes_to_update(args)

    # Do the job
    test_data_path = f"{TEST_FIXTURES_ROOT_PATH}/html"
    with requests.Session() as session:
        for route, filepath in route_file_mapping.items():
            logger.info(f"Updating {test_data_path}{filepath}...")
            logger.info(f"GET {BLIZZARD_HOST}{route}...")
            response = session.get(f"{BLIZZARD_HOST}{route}")
            logger.debug(
                f"HTTP {response.status_code} / Time : {response.elapsed.total_seconds()}"
            )
            if response.status_code == 200:
                save_fixture_file(f"{test_data_path}{filepath}", response.text)
            else:
                logger.error("Error while getting the page : {}", response.text)

    logger.info("Fixtures update finished !")


if __name__ == "__main__":  # pragma: no cover
    logger = logger.patch(lambda record: record.update(name="update_test_fixtures"))
    main()
