"""Player stats summary Parser module"""

from collections import defaultdict
from copy import deepcopy
from typing import ClassVar

from fastapi import status

from app.exceptions import ParserBlizzardError
from app.roles.enums import Role

from ..enums import HeroKey, PlayerGamemode, PlayerPlatform
from ..helpers import get_hero_role, get_plural_stat_key
from .player_career_parser import PlayerCareerParser


class PlayerStatsSummaryParser(PlayerCareerParser):
    """Overwatch player profile page Parser class"""

    generic_stats_names: ClassVar[list] = [
        "games_played",
        "games_won",
        "games_lost",
        "time_played",
    ]
    total_stats_names: ClassVar[list] = [
        "eliminations",
        "assists",
        "deaths",
        "damage",
        "healing",
    ]

    stats_placeholder: ClassVar[dict] = {
        "games_played": 0,
        "games_won": 0,
        "games_lost": 0,
        "time_played": 0,
        "winrate": 0,
        "kda": 0,
        "total": {
            "eliminations": 0,
            "assists": 0,
            "deaths": 0,
            "damage": 0,
            "healing": 0,
        },
    }

    def filter_request_using_query(self, **kwargs) -> dict:
        gamemodes = (
            [kwargs.get("gamemode")]
            if kwargs.get("gamemode")
            else [gamemode.value for gamemode in PlayerGamemode]
        )
        platforms = (
            [kwargs.get("platform")]
            if kwargs.get("platform")
            else [platform.value for platform in PlayerPlatform]
        )

        heroes_stats = self.__compute_heroes_data(gamemodes, platforms)
        if not heroes_stats:
            return {}

        roles_stats = self.__get_roles_stats(heroes_stats)
        general_stats = self.__get_general_stats(roles_stats)

        return {
            "general": general_stats,
            "roles": roles_stats,
            "heroes": heroes_stats,
        }

    async def parse_data(self) -> dict | None:
        # We must check if we have the expected section for profile. If not,
        # it means the player doesn't exist or hasn't been found.
        if not self.root_tag.css_first("blz-section.Profile-masthead"):
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Player not found",
            )

        # Only return heroes stats, which will be used for calculation
        # depending on the parameters
        return self.__get_heroes_stats(self.get_stats())

    def __compute_heroes_data(
        self,
        gamemodes: list[PlayerGamemode],
        platforms: list[PlayerPlatform],
    ) -> dict | None:
        if not self.data:
            return None

        # Compute raw heroes data (every gamemode and platform)
        # into the ones the user want
        computed_heroes_stats = self.__init_heroes_data(gamemodes, platforms)

        # Calculate special values (winrate, kda, averages)
        for hero_key, hero_stats in computed_heroes_stats.items():
            computed_heroes_stats[hero_key]["winrate"] = self.__get_winrate_from_stat(
                hero_stats,
            )
            computed_heroes_stats[hero_key]["kda"] = self.__get_kda_from_stat(
                hero_stats,
            )
            computed_heroes_stats[hero_key]["average"] = self.__get_average_from_stat(
                hero_stats,
            )

        # Only return the heroes for which we have stats
        return {
            hero_key: hero_stats
            for hero_key, hero_stats in computed_heroes_stats.items()
            if hero_stats["time_played"] > 0
        }

    def __init_heroes_data(
        self,
        gamemodes: list[PlayerGamemode],
        platforms: list[PlayerPlatform],
    ) -> dict:
        """Init heroes data by looping over the self.data object. We will
        retrieve the data for all the platforms and gamemodes.
        """
        computed_heroes_stats = {}

        for hero_key, hero_stats in self.data.items():
            computed_heroes_stats[hero_key] = deepcopy(self.stats_placeholder)

            # Retrieve raw data from heroes
            hero_platforms = {
                platform for platform in platforms if platform in hero_stats
            }
            for platform in hero_platforms:
                hero_platform_gamemodes = {
                    gamemode
                    for gamemode in gamemodes
                    if gamemode in hero_stats[platform]
                }

                for gamemode in hero_platform_gamemodes:
                    for stat_name in self.generic_stats_names:
                        computed_heroes_stats[hero_key][stat_name] += hero_stats[
                            platform
                        ][gamemode][stat_name]
                    for stat_name in self.total_stats_names:
                        computed_heroes_stats[hero_key]["total"][stat_name] += (
                            hero_stats[platform][gamemode]["total"][stat_name]
                        )

        return computed_heroes_stats

    @staticmethod
    def _get_category_stats(category: str, hero_stats: list[dict]) -> dict:
        category_stats = filter(lambda x: x["category"] == category, hero_stats)
        try:
            return next(category_stats)["stats"]
        except StopIteration:
            return {}

    @staticmethod
    def _get_stat_value(stat_name: str, stats_list: list[dict]) -> int | float:
        stat_value = filter(
            lambda x: get_plural_stat_key(x["key"]) == stat_name,
            stats_list,
        )
        try:
            return next(stat_value)["value"]
        except StopIteration:
            return 0

    def __get_heroes_stats(self, raw_stats: dict | None) -> dict | None:
        if not raw_stats:
            return None

        # Filter only platforms with stats
        raw_heroes_stats = {
            platform: platform_stats
            for platform, platform_stats in raw_stats.items()
            if platform_stats
        }

        # Compute the data
        heroes_stats = self.__compute_heroes_stats(raw_heroes_stats)

        # Only return heroes for which we have stats
        return {
            hero_key: hero_stat
            for hero_key, hero_stat in heroes_stats.items()
            if hero_stat
        }

    def __compute_heroes_stats(self, raw_heroes_stats: dict) -> dict:
        """Compute heroes stats for every gamemode and platform."""
        heroes_stats = {hero_key: defaultdict(dict) for hero_key in HeroKey}

        for platform, platform_stats in raw_heroes_stats.items():
            platform_gamemodes_stats = {
                gamemode: gamemode_stats
                for gamemode, gamemode_stats in platform_stats.items()
                if gamemode_stats
            }

            for gamemode, gamemode_stats in platform_gamemodes_stats.items():
                career_stats = {
                    hero_key: hero_stats
                    for hero_key, hero_stats in gamemode_stats["career_stats"].items()
                    if hero_stats and hero_key != "all-heroes"
                }

                for hero_key, hero_stats in career_stats.items():
                    heroes_stats[hero_key][platform][gamemode] = (
                        self.__compute_hero_stats(hero_stats)
                    )

        return heroes_stats

    def __compute_hero_stats(self, hero_stats: dict) -> dict:
        """Compute a single hero statistics."""

        game_stats = self._get_category_stats("game", hero_stats)
        games_played = self._get_stat_value("games_played", game_stats)
        time_played = self._get_stat_value("time_played", game_stats)
        games_lost = self._get_stat_value("games_lost", game_stats)

        # Sometimes, games lost are negative on Blizzard page. To not
        # disturbate too much the winrate, I decided to put a value
        # in order for the player to have 50% winrate
        games_lost = round(games_played / 2) if games_lost < 0 else games_lost

        # We just calculate games won like this because sometimes Blizzard
        # exposes "Games Won" stats several times for the same hero and
        # not with the same value, but it doesn't happen for games lost
        games_won = games_played - games_lost

        # Make sure it's not negative
        games_won = max(games_won, 0)

        combat_stats = self._get_category_stats("combat", hero_stats)
        eliminations = self._get_stat_value("eliminations", combat_stats)
        deaths = self._get_stat_value("deaths", combat_stats)
        damage = self._get_stat_value("all_damage_done", combat_stats)

        assists_stats = self._get_category_stats("assists", hero_stats)
        assists = self._get_stat_value("offensive_assists", assists_stats)
        healing = self._get_stat_value("healing_done", assists_stats)

        return {
            "games_played": games_played,
            "games_won": games_won,
            "games_lost": games_lost,
            "time_played": time_played,
            "total": {
                "eliminations": eliminations,
                "assists": assists,
                "deaths": deaths,
                "damage": damage,
                "healing": healing,
            },
        }

    def __get_roles_stats(self, heroes_stats: dict) -> dict:
        # Initialize stats
        roles_stats = {role_key: deepcopy(self.stats_placeholder) for role_key in Role}

        # Retrieve raw data from heroes
        for hero_key, hero_stats in heroes_stats.items():
            hero_role = get_hero_role(hero_key)
            for stat_name in self.generic_stats_names:
                roles_stats[hero_role][stat_name] += hero_stats[stat_name]
            for stat_name in self.total_stats_names:
                roles_stats[hero_role]["total"][stat_name] += hero_stats["total"][
                    stat_name
                ]

        # Calculate special values (winrate, kda, averages)
        for role_key, role_stat in roles_stats.items():
            roles_stats[role_key]["winrate"] = self.__get_winrate_from_stat(role_stat)
            roles_stats[role_key]["kda"] = self.__get_kda_from_stat(role_stat)
            roles_stats[role_key]["average"] = self.__get_average_from_stat(role_stat)

        # Only return the roles for which the player has played
        return {
            role_key: role_stat
            for role_key, role_stat in roles_stats.items()
            if role_stat["time_played"] > 0
        }

    def __get_general_stats(self, roles_stats: dict) -> dict:
        general_stats = deepcopy(self.stats_placeholder)

        # Retrieve raw data from roles
        for role_stat in roles_stats.values():
            for stat_name in self.generic_stats_names:
                general_stats[stat_name] += role_stat[stat_name]
            for stat_name in self.total_stats_names:
                general_stats["total"][stat_name] += role_stat["total"][stat_name]

        # Calculate special values (winrate, kda, averages)
        general_stats["winrate"] = self.__get_winrate_from_stat(general_stats)
        general_stats["kda"] = self.__get_kda_from_stat(general_stats)
        general_stats["average"] = self.__get_average_from_stat(general_stats)

        return general_stats

    def __get_winrate_from_stat(self, stat: dict) -> float:
        return self.__get_winrate(
            stat.get("games_won") or 0,
            stat.get("games_played") or 0,
        )

    @staticmethod
    def __get_winrate(games_won: int, games_played: int) -> float:
        return 0 if games_played <= 0 else round((games_won / games_played) * 100, 2)

    def __get_kda_from_stat(self, stat: dict) -> float:
        return self.__get_kda(
            stat["total"]["eliminations"] or 0,
            stat["total"]["assists"] or 0,
            stat["total"]["deaths"] or 0,
        )

    @staticmethod
    def __get_kda(eliminations: int, assists: int, deaths: int) -> float:
        return round((eliminations + assists) / deaths, 2) if deaths > 0 else 0

    @staticmethod
    def __get_average_from_stat(stat: dict):
        ten_minutes_played = stat["time_played"] / 600
        return {
            key: (
                round(stat["total"][key] / ten_minutes_played, 2)
                if ten_minutes_played > 0
                else 0
            )
            for key in stat["total"]
        }
