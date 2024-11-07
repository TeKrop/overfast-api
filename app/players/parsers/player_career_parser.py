"""Player profile page Parser module"""

from typing import ClassVar

from bs4 import Tag
from fastapi import status

from app.config import settings
from app.exceptions import ParserBlizzardError

from ..enums import (
    CareerHeroesComparisonsCategory,
    CompetitiveRole,
    PlayerGamemode,
    PlayerPlatform,
)
from ..helpers import (
    get_computed_stat_value,
    get_division_from_icon,
    get_endorsement_value_from_frame,
    get_hero_keyname,
    get_player_title,
    get_plural_stat_key,
    get_real_category_name,
    get_role_key_from_icon,
    get_stats_hero_class,
    get_tier_from_icon,
    string_to_snakecase,
)
from .base_player_parser import BasePlayerParser
from .search_data_parser import LastUpdatedAtParser, NamecardParser

platforms_div_mapping = {
    PlayerPlatform.PC: "mouseKeyboard-view",
    PlayerPlatform.CONSOLE: "controller-view",
}
gamemodes_div_mapping = {
    PlayerGamemode.QUICKPLAY: "quickPlay-view",
    PlayerGamemode.COMPETITIVE: "competitive-view",
}


class PlayerCareerParser(BasePlayerParser):
    """Overwatch player profile page Parser class"""

    root_path = settings.career_path
    timeout = settings.career_path_cache_timeout
    valid_http_codes: ClassVar[list] = [
        200,  # Classic response
        404,  # Player Not Found response, we want to handle it here
    ]

    # Filters coming from user query
    filters: ClassVar[dict[str, bool | str]]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_filters(**kwargs)

    def _init_filters(self, **kwargs) -> None:
        self.filters = {
            filter_key: kwargs.get(filter_key)
            for filter_key in ("summary", "stats", "platform", "gamemode", "hero")
        }

    def filter_request_using_query(self, **_) -> dict:
        if self.filters["summary"]:
            return self.data.get("summary")

        if self.filters["stats"]:
            return self._filter_stats()

        return {
            "summary": self.data["summary"],
            "stats": self._filter_all_stats_data(),
        }

    def _filter_stats(self) -> dict:
        filtered_data = self.data["stats"] or {}

        # We must have a valid platform filter here
        platform = self.filters["platform"]
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

        filtered_data = filtered_data.get(self.filters["gamemode"]) or {}
        if not filtered_data:
            return {}

        filtered_data = filtered_data.get("career_stats") or {}
        hero_filter = self.filters["hero"]

        return {
            hero_key: statistics
            for hero_key, statistics in filtered_data.items()
            if not hero_filter or hero_filter == hero_key
        }

    def _filter_all_stats_data(self) -> dict:
        stats_data = self.data["stats"] or {}

        # Return early if no platform or gamemode is specified
        if not self.filters["platform"] and not self.filters["gamemode"]:
            return stats_data

        filtered_data = {}

        for platform_key, platform_data in stats_data.items():
            if self.filters["platform"] and platform_key != self.filters["platform"]:
                filtered_data[platform_key] = None
                continue

            if platform_data is None:
                filtered_data[platform_key] = None
                continue

            if self.filters["gamemode"] is None:
                filtered_data[platform_key] = platform_data
                continue

            filtered_data[platform_key] = {
                gamemode_key: (
                    gamemode_data if gamemode_key == self.filters["gamemode"] else None
                )
                for gamemode_key, gamemode_data in platform_data.items()
            }

        return filtered_data

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
        # If the user filtered the page on stats, no need to parse the summary
        if self.filters["stats"]:
            return {}

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
            "username": str(
                summary_div.find("h1", class_="Profile-player--name").contents[0]
            ),
            "avatar": (
                summary_div.find(
                    "img",
                    class_="Profile-player--portrait",
                    recursive=False,
                ).get("src")
            ),
            "namecard": self.__get_namecard_url(),
            "title": self.__get_title(profile_div),
            "endorsement": self.__get_endorsement(progression_div),
            "competitive": self.__get_competitive_ranks(progression_div),
            "last_updated_at": self.__get_last_updated_at_value(),
        }

    def __get_namecard_url(self) -> str | None:
        return NamecardParser(player_id=self.player_id).retrieve_data_value(
            self.player_data["summary"]
        )

    def __get_last_updated_at_value(self) -> int | None:
        return LastUpdatedAtParser(player_id=self.player_id).retrieve_data_value(
            self.player_data["summary"]
        )

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
        title = str(title_tag.contents[0]) or None

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
        profile_section = self.root_tag.find(
            "div",
            class_=platform_class,
            recursive=False,
        )
        if not profile_section:
            return None

        statistics_section = profile_section.find(
            "blz-section",
            class_="competitive-view",
            recursive=False,
        )

        last_season_played = statistics_section.get("data-latestherostatrankseasonow2")
        return int(last_season_played) if last_season_played else None

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
        # If the user filtered the page on summary, no need to parse the stats
        if self.filters["summary"]:
            return None

        stats = {
            platform.value: self.__get_platform_stats(platform, platform_class)
            for platform, platform_class in platforms_div_mapping.items()
        }

        # If we don't have data for any platform and we're consulting stats, return None directly
        return None if not any(stats.values()) and self.filters["stats"] else stats

    def __get_platform_stats(
        self, platform: PlayerPlatform, platform_class: str
    ) -> dict | None:
        # If the user decided to filter on another platform, stop here
        if self.filters["platform"] and self.filters["platform"] != platform:
            return None

        statistics_section = self.root_tag.find(
            "div", class_=platform_class, recursive=False
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
        # If the user decided to filter on another gamemode, stop here
        if self.filters["gamemode"] and self.filters["gamemode"] != gamemode:
            return None

        if not statistics_section:
            return None

        top_heroes_section = statistics_section.find(
            "blz-section",
            class_="Profile-heroSummary",
            recursive=False,
        ).find(
            "div",
            class_=gamemodes_div_mapping[gamemode],
            recursive=False,
        )

        # Check if we can find a select in the section. If not, it means there is
        # no data to show for this gamemode and platform, return nothing.
        if not top_heroes_section.find("select"):
            return None

        career_stats_section = statistics_section.find(
            "blz-section",
            class_=gamemodes_div_mapping[gamemode],
            recursive=False,
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
                .find("select", recursive=False)
                .children
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
                        # First div is "Profile-progressBar--bar"
                        "hero": progress_bar_container.contents[0]["data-hero-id"],
                        # Second div is "Profile-progressBar--textWrapper"
                        "value": get_computed_stat_value(
                            # Second div is "Profile-progressBar-description"
                            str(
                                progress_bar_container.contents[1]
                                .contents[1]
                                .contents[0]
                            ),
                        ),
                    }
                    for progress_bar in category.children
                    for progress_bar_container in progress_bar.children
                    if progress_bar_container.name == "div"
                ],
            }
            for category in top_heroes_section.children
            if (
                "Profile-progressBars" in category["class"]
                and category["data-category-id"] in categories
            )
        }

        for category in CareerHeroesComparisonsCategory:
            # Sometimes, Blizzard exposes the categories without any value
            # In that case, we must assume we have no data at all
            if (
                category.value not in heroes_comparisons
                or not heroes_comparisons[category.value]["values"]
            ):
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
                .find("select", recursive=False)
                .children
            )
            if option.get("option-id")
        }

        career_stats = {}

        for hero_container in career_stats_section.children:
            # Hero container should be span with "stats-container" class
            if hero_container.name != "span":
                continue

            stats_hero_class = get_stats_hero_class(hero_container["class"])

            # Sometimes, Blizzard makes some weird things and options don't
            # have any label, so we can't know for sure which hero it is about.
            # So we have to skip this field
            if stats_hero_class not in heroes_options:
                continue

            hero_key = get_hero_keyname(heroes_options[stats_hero_class])

            career_stats[hero_key] = []
            # Hero container children are div with "category" class
            for card_stat in hero_container.children:
                # Content div should be the only child ("content" class)
                content_div = card_stat.contents[0]

                # Label should be the first div within content ("header" class)
                category_label = str(content_div.contents[0].contents[0].contents[0])

                career_stats[hero_key].append(
                    {
                        "category": string_to_snakecase(category_label),
                        "label": category_label,
                        "stats": [],
                    },
                )
                for stat_row in content_div.children:
                    if "stat-item" not in stat_row["class"]:
                        continue

                    stat_name = str(stat_row.contents[0].contents[0])
                    career_stats[hero_key][-1]["stats"].append(
                        {
                            "key": get_plural_stat_key(string_to_snakecase(stat_name)),
                            "label": stat_name,
                            "value": get_computed_stat_value(
                                str(stat_row.contents[1].contents[0]),
                            ),
                        },
                    )

            # For a reason, sometimes the hero is in the dropdown but there
            # is no stat to show. In this case, return None as if there was
            # no stat at all
            if len(career_stats[hero_key]) == 0:
                del career_stats[hero_key]

        return career_stats
