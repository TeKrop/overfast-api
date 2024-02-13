"""Player profile page Parser module"""
from typing import ClassVar

from bs4 import Tag
from fastapi import status

from app.common.enums import (
    CareerHeroesComparisonsCategory,
    CompetitiveRole,
    PlayerGamemode,
    PlayerPlatform,
)
from app.common.exceptions import ParserBlizzardError
from app.common.helpers import get_player_title
from app.config import settings

from .generics.api_parser import APIParser
from .helpers import (
    get_computed_stat_value,
    get_division_from_icon,
    get_endorsement_value_from_frame,
    get_hero_keyname,
    get_plural_stat_key,
    get_real_category_name,
    get_role_key_from_icon,
    get_stats_hero_class,
    get_tier_from_icon,
    string_to_snakecase,
)

platforms_div_mapping = {
    PlayerPlatform.PC: "mouseKeyboard-view",
    PlayerPlatform.CONSOLE: "controller-view",
}
gamemodes_div_mapping = {
    PlayerGamemode.QUICKPLAY: "quickPlay-view",
    PlayerGamemode.COMPETITIVE: "competitive-view",
}


class PlayerParser(APIParser):
    """Overwatch player profile page Parser class"""

    root_path = settings.career_path
    timeout = settings.career_path_cache_timeout
    valid_http_codes: ClassVar[list] = [
        200,  # Classic response
        404,  # Player Not Found response, we want to handle it here
    ]
    cache_expiration_timeout = settings.career_parser_cache_expiration_timeout

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_id = kwargs.get("player_id")

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{super().get_blizzard_url(**kwargs)}/{kwargs.get('player_id')}/"

    def filter_request_using_query(self, **kwargs) -> dict:
        if kwargs.get("summary"):
            return self.data.get("summary")

        return self._filter_stats(**kwargs) if kwargs.get("stats") else self.data

    def _filter_stats(self, **kwargs) -> dict:
        filtered_data = self.data["stats"] or {}

        platform = kwargs.get("platform")
        if not platform:
            # Retrieve a "default" platform is the user didn't provided one
            if possible_platforms := [
                platform_key
                for platform_key, platform_data in filtered_data.items()
                if platform_data is not None
            ]:
                # Take the first one of the list, usually there will be only one.
                # If there are two, the PC stats should come first
                platform = possible_platforms[0]
            else:
                return {}
        filtered_data = filtered_data.get(platform) or {}
        if not filtered_data:
            return {}

        filtered_data = filtered_data.get(kwargs.get("gamemode")) or {}
        if not filtered_data:
            return {}

        filtered_data = filtered_data.get("career_stats") or {}
        hero_filter = kwargs.get("hero")

        return {
            hero_key: statistics
            for hero_key, statistics in filtered_data.items()
            if not hero_filter or hero_filter == hero_key
        }

    def parse_data(self) -> dict:
        # We must check if we have the expected section for profile. If not,
        # it means the player doesn't exist or hasn't been found.
        if not self.root_tag.find("blz-section", class_="Profile-masthead"):
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Player not found",
            )

        return {"summary": self.__get_summary(), "stats": self.get_stats()}

    def __get_summary(self) -> dict:
        profile_div = self.root_tag.find(
            "blz-section",
            class_="Profile-masthead",
            recursive=False,
        ).find("div", class_="Profile-player", recursive=False)
        summary_div = profile_div.find(
            "div",
            class_="Profile-player--summaryWrapper",
            recursive=False,
        )
        progression_div = profile_div.find(
            "div",
            class_="Profile-player--info",
            recursive=False,
        )

        return {
            "username": (
                summary_div.find("h1", class_="Profile-player--name").get_text()
            ),
            "avatar": (
                summary_div.find(
                    "img",
                    class_="Profile-player--portrait",
                    recursive=False,
                ).get("src")
            ),
            "title": self.__get_title(profile_div),
            "endorsement": self.__get_endorsement(progression_div),
            "competitive": self.__get_competitive_ranks(progression_div),
        }

    @staticmethod
    def __get_title(profile_div: Tag) -> str | None:
        # We return None is there isn't any player title div
        if not (
            title_tag := profile_div.find(
                "h2",
                class_="Profile-player--title",
                recursive=False,
            )
        ):
            return None

        # Retrieve the title text
        title = title_tag.get_text() or None

        # Special case : the "no title" means there is no title
        return get_player_title(title)

    @staticmethod
    def __get_endorsement(progression_div: Tag) -> dict | None:
        endorsement_span = progression_div.find(
            "span",
            class_="Profile-player--endorsementWrapper",
            recursive=False,
        )
        if not endorsement_span:
            return None

        endorsement_frame_url = endorsement_span.find(
            "img",
            class_="Profile-playerSummary--endorsement",
        )["src"]

        return {
            "level": get_endorsement_value_from_frame(endorsement_frame_url),
            "frame": endorsement_frame_url,
        }

    def __get_competitive_ranks(self, progression_div: Tag) -> dict | None:
        competitive_ranks = {
            platform.value: self.__get_platform_competitive_ranks(
                progression_div,
                platform_class,
            )
            for platform, platform_class in platforms_div_mapping.items()
        }

        # If we don't have data for any platform, return None directly
        return None if not any(competitive_ranks.values()) else competitive_ranks

    def __get_platform_competitive_ranks(
        self,
        progression_div: Tag,
        platform_class: str,
    ) -> dict | None:
        last_season_played = self.__get_last_season_played(platform_class)

        competitive_rank_div = progression_div.select_one(
            f"div.Profile-playerSummary--rankWrapper.{platform_class}",
        )
        role_wrappers = competitive_rank_div.find_all(
            "div",
            class_="Profile-playerSummary--roleWrapper",
            recursive=False,
        )
        if not role_wrappers and not last_season_played:
            return None

        competitive_ranks = {}

        for role_wrapper in role_wrappers:
            role_icon = self.__get_role_icon(role_wrapper)
            role_key = get_role_key_from_icon(role_icon).value

            rank_tier_icons = role_wrapper.find_all(
                "img", class_="Profile-playerSummary--rank"
            )
            rank_icon, tier_icon = rank_tier_icons[0]["src"], rank_tier_icons[1]["src"]

            competitive_ranks[role_key] = {
                "division": get_division_from_icon(rank_icon).value,
                "tier": get_tier_from_icon(tier_icon),
                "role_icon": role_icon,
                "rank_icon": rank_icon,
                "tier_icon": tier_icon,
            }

        for role in CompetitiveRole:
            if role.value not in competitive_ranks:
                competitive_ranks[role.value] = None

        competitive_ranks["season"] = last_season_played

        return competitive_ranks

    def __get_last_season_played(self, platform_class: str) -> int | None:
        profile_section = self.root_tag.select_one(f"div.Profile-view.{platform_class}")
        if not profile_section:
            return None

        statistics_section = profile_section.select_one(
            "blz-section.stats.competitive-view",
        )
        return (
            int(statistics_section["data-latestherostatrankseasonow2"])
            if (
                statistics_section
                and "data-latestherostatrankseasonow2" in statistics_section.attrs
            )
            else None
        )

    @staticmethod
    def __get_role_icon(role_wrapper: Tag) -> str:
        """The role icon format may differ depending on the platform : img for
        PC players, svg for console players
        """
        if role_div := role_wrapper.find("div", class_="Profile-playerSummary--role"):
            return role_div.find("img")["src"]

        role_svg = role_wrapper.find("svg", class_="Profile-playerSummary--role")
        return role_svg.find("use")["xlink:href"]

    def get_stats(self) -> dict | None:
        stats = {
            platform.value: self.__get_platform_stats(platform_class)
            for platform, platform_class in platforms_div_mapping.items()
        }

        # If we don't have data for any platform, return None directly
        return None if not any(stats.values()) else stats

    def __get_platform_stats(self, platform_class: str) -> dict | None:
        statistics_section = self.root_tag.select_one(
            f"div.Profile-view.{platform_class}",
        )
        gamemodes_infos = {
            gamemode.value: self.__get_gamemode_infos(statistics_section, gamemode)
            for gamemode in PlayerGamemode
        }

        # If we don't have data for any gamemode for the given platform,
        # return None directly
        return None if not any(gamemodes_infos.values()) else gamemodes_infos

    def __get_gamemode_infos(
        self,
        statistics_section: Tag,
        gamemode: PlayerGamemode,
    ) -> dict | None:
        if not statistics_section:
            return None

        top_heroes_section = statistics_section.find(
            "blz-section",
            class_="Profile-heroSummary",
            recursive=False,
        ).select_one(f"div.Profile-heroSummary--view.{gamemodes_div_mapping[gamemode]}")

        # Check if we can find a select in the section. If not, it means there is
        # no data to show for this gamemode and platform, return nothing.
        if not top_heroes_section.find("select"):
            return None

        career_stats_section = statistics_section.select_one(
            f"blz-section.stats.{gamemodes_div_mapping[gamemode]}",
        )

        return {
            "heroes_comparisons": self.__get_heroes_comparisons(top_heroes_section),
            "career_stats": self.__get_career_stats(career_stats_section),
        }

    def __get_heroes_comparisons(self, top_heroes_section: Tag) -> dict:
        categories = {
            option["value"]: option["option-id"]
            for option in (
                top_heroes_section.find(
                    "div",
                    class_="Profile-heroSummary--header",
                    recursive=False,
                )
                .find("select")
                .find_all("option")
            )
            if option.get("option-id")
        }

        heroes_comparisons = {
            string_to_snakecase(
                get_real_category_name(categories[category["data-category-id"]]),
            ): {
                "label": get_real_category_name(
                    categories[category["data-category-id"]],
                ),
                "values": [
                    {
                        "hero": (
                            progress_bar.find("div", class_="Profile-progressBar--bar")[
                                "data-hero-id"
                            ]
                        ),
                        "value": get_computed_stat_value(
                            progress_bar.find(
                                "div",
                                class_="Profile-progressBar-description",
                            ).get_text(),
                        ),
                    }
                    for progress_bar in category.find_all(
                        "div",
                        class_="Profile-progressBar",
                        recursive=False,
                    )
                ],
            }
            for category in top_heroes_section.find_all(
                "div",
                class_="Profile-progressBars",
                recursive=False,
            )
            if category["data-category-id"] in categories
        }

        for category in CareerHeroesComparisonsCategory:
            if category.value not in heroes_comparisons:
                heroes_comparisons[category.value] = None

        return heroes_comparisons

    @staticmethod
    def __get_career_stats(career_stats_section: Tag) -> dict:
        heroes_options = {
            f"option-{option['value']}": option["option-id"]
            for option in (
                career_stats_section.find(
                    "div",
                    class_="Profile-heroSummary--header",
                    recursive=False,
                )
                .find("select")
                .find_all("option")
            )
            if option.get("option-id")
        }

        career_stats = {}

        for hero_container in career_stats_section.find_all(
            "span",
            class_="stats-container",
            recursive=False,
        ):
            stats_hero_class = get_stats_hero_class(hero_container["class"])

            # Sometimes, Blizzard makes some weird things and options don't
            # have any label, so we can't know for sure which hero it is about.
            # So we have to skip this field
            if stats_hero_class not in heroes_options:
                continue

            hero_key = get_hero_keyname(heroes_options[stats_hero_class])

            career_stats[hero_key] = []
            for card_stat in hero_container.find_all(
                "div",
                class_="category",
                recursive=False,
            ):
                content_div = card_stat.find("div", class_="content", recursive=False)
                category_label = content_div.find(
                    "div",
                    class_="header",
                    recursive=False,
                ).get_text()

                career_stats[hero_key].append(
                    {
                        "category": string_to_snakecase(category_label),
                        "label": category_label,
                        "stats": [],
                    },
                )
                for stat_row in content_div.find_all("div", class_="stat-item"):
                    stat_name = stat_row.find("p", class_="name").get_text()
                    career_stats[hero_key][-1]["stats"].append(
                        {
                            "key": get_plural_stat_key(string_to_snakecase(stat_name)),
                            "label": stat_name,
                            "value": get_computed_stat_value(
                                stat_row.find("p", class_="value").get_text(),
                            ),
                        },
                    )

            # For a reason, sometimes the hero is in the dropdown but there
            # is no stat to show. In this case, return None as if there was
            # no stat at all
            if len(career_stats[hero_key]) == 0:
                del career_stats[hero_key]

        return career_stats
