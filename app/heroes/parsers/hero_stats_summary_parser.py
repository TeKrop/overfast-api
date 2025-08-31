"""Search Data Parser module"""

from typing import ClassVar

from fastapi import status

from app.config import settings
from app.exceptions import ParserBlizzardError
from app.parsers import JSONParser
from app.players.enums import PlayerGamemode, PlayerPlatform


class HeroStatsSummaryParser(JSONParser):
    """Static Data Parser class"""

    request_headers_headers: ClassVar[dict] = JSONParser.request_headers | {
        "X-Requested-With": "XMLHttpRequest"
    }

    root_path: str = settings.hero_stats_path

    platform_mapping: ClassVar[dict[PlayerPlatform, str]] = {
        PlayerPlatform.PC: "PC",
        PlayerPlatform.CONSOLE: "Console",
    }

    gamemode_mapping: ClassVar[dict[PlayerGamemode, str]] = {
        PlayerGamemode.QUICKPLAY: "0",
        PlayerGamemode.COMPETITIVE: "1",
    }

    def __init__(self, **kwargs):
        # Mandatory query params
        self.platform_filter: str = self.platform_mapping[kwargs["platform"]]
        self.gamemode = kwargs["gamemode"]
        self.gamemode_filter: str = self.gamemode_mapping[self.gamemode]
        self.region_filter: str = kwargs["region"].capitalize()

        # Optional query params
        self.map_filter: str = kwargs.get("map") or "all-maps"
        self.role_filter: str | None = kwargs.get("role")
        self.competitive_division_filter: str = (
            kwargs.get("competitive_division") or "all"
        ).capitalize()
        self.order_by: str | None = kwargs.get("order_by")

        super().__init__(**kwargs)

    async def parse_data(self) -> list[dict]:
        """
        Parses and filters hero data from the loaded JSON based on the current filters.

        Returns:
            list[dict]: A list of dictionaries containing hero stats data.

        Raises:
            ParserBlizzardError: If the selected map does not match the gamemode in the filters.
        """
        # Check if the data matches the expected map filter
        self.check_data_validity()

        # Role filter isn't applied server-side, so we filter it here if provided.
        hero_stats_data = self.filter_heroes()

        # Only retrieve needed data
        hero_stats_data = self.apply_transformations(hero_stats_data)

        # Apply ordering before returning
        return self.apply_ordering(hero_stats_data)

    def check_data_validity(self) -> None:
        """
        Validates that the selected map matches the current gamemode.

        Raises:
            ParserBlizzardError: If the selected map does not match the gamemode.
        """
        if self.map_filter != self.json_data["selected"]["map"]:
            raise ParserBlizzardError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=(
                    f"Selected map '{self.map_filter}' is not compatible with '{self.gamemode}' gamemode."
                ),
            )

    def filter_heroes(self) -> list[dict]:
        """
        Filters hero statistics based on the current role filter.

        Returns:
            list[dict]: A list of hero entries matching the role filter (if provided).
        """
        return [
            rate
            for rate in self.json_data["rates"]
            if (
                self.role_filter is None
                or rate["hero"]["role"].lower() == self.role_filter
            )
        ]

    def apply_transformations(self, hero_stats_data: list[dict]) -> list[dict]:
        """
        Extracts and structures relevant hero statistics fields from the filtered data.

        Args:
            hero_stats_data (list[dict]): The filtered list of hero data.

        Returns:
            list[dict]: A list of dictionaries, each containing only the key statistics fields for a hero.
        """
        return [
            {
                "hero": rate["id"],
                "pickrate": rate["cells"]["pickrate"],
                "winrate": rate["cells"]["winrate"],
            }
            for rate in hero_stats_data
        ]

    def apply_ordering(self, hero_stats_data: list[dict]) -> list[dict]:
        """
        Orders the hero statistics data based on the specified field and direction.

        Returns:
            list[dict]: The input list, sorted according to the provided ordering.
        """
        order_field, order_arrangement = self.order_by.split(":")
        hero_stats_data.sort(
            key=lambda hero_stat: hero_stat[order_field],
            reverse=order_arrangement == "desc",
        )
        return hero_stats_data

    def get_blizzard_query_params(self, **kwargs) -> dict:
        """
        Constructs a dictionary of query parameters for a Blizzard API request based
        on the current filter attributes and additional keyword arguments.

        Args:
            **kwargs: Additional keyword arguments that may influence the query parameters.
                - gamemode (PlayerGamemode): The game mode being queried. If set to PlayerGamemode.COMPETITIVE,
                  the 'tier' parameter will be included based on the competitive division filter.

        Returns:
            dict: A dictionary containing the Blizzard API query parameters, including platform, game mode,
                  region, and map filters. If the game mode is competitive, the competitive division tier is also included.
        """
        blizzard_query_params = {
            "input": self.platform_filter,
            "rq": self.gamemode_filter,
            "region": self.region_filter,
            "map": self.map_filter,
        }

        if kwargs["gamemode"] == PlayerGamemode.COMPETITIVE:
            blizzard_query_params["tier"] = self.competitive_division_filter

        return blizzard_query_params
