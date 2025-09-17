"""Player profile page Parser module"""

from typing import ClassVar

from fastapi import status
from selectolax.lexbor import LexborNode

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

    async def parse_data(self) -> dict:
        # We must check if we have the expected section for profile. If not,
        # it means the player doesn't exist or hasn't been found.
        if not self.root_tag.css_first("blz-section.Profile-masthead"):
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Player not found",
            )

        return {"summary": self.__get_summary(), "stats": self.get_stats()}

    def __get_summary(self) -> dict:
        # If the user filtered the page on stats, no need to parse the summary
        if self.filters["stats"]:
            return {}

        profile_div = self.root_tag.css_first(
            "blz-section.Profile-masthead > div.Profile-player"
        )
        summary_div = profile_div.css_first("div.Profile-player--summaryWrapper")
        progression_div = profile_div.css_first("div.Profile-player--info")

        return {
            "username": summary_div.css_first("h1.Profile-player--name").text(),
            "avatar": self.player_data["summary"]["avatar"],
            "namecard": self.player_data["summary"].get("namecard"),
            "title": get_player_title(self.player_data["summary"]["title"]),
            "endorsement": self.__get_endorsement(progression_div),
            "competitive": self.__get_competitive_ranks(progression_div),
            "last_updated_at": self.player_data["summary"]["lastUpdated"],
        }

    @staticmethod
    def __get_endorsement(progression_div: LexborNode) -> dict | None:
        endorsement_span = progression_div.css_first(
            "span.Profile-player--endorsementWrapper"
        )
        if not endorsement_span:
            return None

        endorsement_frame_url = endorsement_span.css_first(
            "img.Profile-playerSummary--endorsement"
        ).attributes["src"]

        return {
            "level": get_endorsement_value_from_frame(endorsement_frame_url),
            "frame": endorsement_frame_url,
        }

    def __get_competitive_ranks(self, progression_div: LexborNode) -> dict | None:
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
        progression_div: LexborNode,
        platform_class: str,
    ) -> dict | None:
        last_season_played = self.__get_last_season_played(platform_class)

        role_wrappers = progression_div.css(
            f"div.Profile-playerSummary--rankWrapper.{platform_class} > div.Profile-playerSummary--roleWrapper",
        )
        if not role_wrappers and not last_season_played:
            return None

        competitive_ranks = {}

        for role_wrapper in role_wrappers:
            role_icon = self.__get_role_icon(role_wrapper)
            role_key = get_role_key_from_icon(role_icon).value

            rank_tier_icons = role_wrapper.css("img.Profile-playerSummary--rank")
            rank_icon, tier_icon = (
                rank_tier_icons[0].attributes["src"],
                rank_tier_icons[1].attributes["src"],
            )

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
        if not (profile_section := self.__get_profile_view_section(platform_class)):
            return None

        statistics_section = profile_section.css_first(
            "blz-section.stats.competitive-view"
        )
        last_season_played = statistics_section.attributes.get(
            "data-latestherostatrankseasonow2"
        )
        return int(last_season_played) if last_season_played else None

    def __get_profile_view_section(self, platform_class: str) -> LexborNode:
        return self.root_tag.css_first(f"div.Profile-view.{platform_class}")

    @staticmethod
    def __get_role_icon(role_wrapper: LexborNode) -> str:
        """The role icon format may differ depending on the platform : img for
        PC players, svg for console players
        """
        if role_div := role_wrapper.css_first("div.Profile-playerSummary--role"):
            return role_div.css_first("img").attributes["src"]

        role_svg = role_wrapper.css_first("svg.Profile-playerSummary--role")
        return role_svg.css_first("use").attributes["xlink:href"]

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

        statistics_section = self.__get_profile_view_section(platform_class)
        gamemodes_infos = {
            gamemode.value: self.__get_gamemode_infos(statistics_section, gamemode)
            for gamemode in PlayerGamemode
        }

        # If we don't have data for any gamemode for the given platform,
        # return None directly
        return None if not any(gamemodes_infos.values()) else gamemodes_infos

    def __get_gamemode_infos(
        self,
        statistics_section: LexborNode,
        gamemode: PlayerGamemode,
    ) -> dict | None:
        # If the user decided to filter on another gamemode, stop here
        if self.filters["gamemode"] and self.filters["gamemode"] != gamemode:
            return None

        if not statistics_section:
            return None

        top_heroes_section = statistics_section.first_child.css_first(
            f"div.{gamemodes_div_mapping[gamemode]}"
        )

        # Check if we can find a select in the section. If not, it means there is
        # no data to show for this gamemode and platform, return nothing.
        if not top_heroes_section.css_first("select"):
            return None

        career_stats_section = statistics_section.css_first(
            f"blz-section.{gamemodes_div_mapping[gamemode]}"
        )
        return {
            "heroes_comparisons": self.__get_heroes_comparisons(top_heroes_section),
            "career_stats": self.__get_career_stats(career_stats_section),
        }

    def __get_heroes_comparisons(self, top_heroes_section: LexborNode) -> dict:
        categories = self.__get_heroes_options(top_heroes_section)

        heroes_comparisons = {
            string_to_snakecase(
                get_real_category_name(
                    categories[category.attributes["data-category-id"]]
                ),
            ): {
                "label": get_real_category_name(
                    categories[category.attributes["data-category-id"]],
                ),
                "values": [
                    {
                        # Normally, a valid data-hero-id is present. However, in some
                        # cases — such as when a hero is newly available for testing —
                        # stats may lack an associated ID. In these instances, we fall
                        # back to using the hero's title in lowercase.
                        "hero": (
                            progress_bar_container.first_child.attributes.get(
                                "data-hero-id"
                            )
                            or progress_bar_container.last_child.first_child.text().lower()
                        ),
                        "value": get_computed_stat_value(
                            progress_bar_container.last_child.last_child.text()
                        ),
                    }
                    for progress_bar in category.iter()
                    for progress_bar_container in progress_bar.iter()
                    if progress_bar_container.tag == "div"
                ],
            }
            for category in top_heroes_section.iter()
            if (
                "Profile-progressBars" in category.attributes["class"]
                and category.attributes["data-category-id"] in categories
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

    def __get_career_stats(self, career_stats_section: LexborNode) -> dict:
        heroes_options = self.__get_heroes_options(
            career_stats_section, key_prefix="option-"
        )

        career_stats = {}

        for hero_container in career_stats_section.iter():
            # Hero container should be span with "stats-container" class
            if hero_container.tag != "span":
                continue

            stats_hero_class = get_stats_hero_class(hero_container.attributes["class"])

            # Sometimes, Blizzard makes some weird things and options don't
            # have any label, so we can't know for sure which hero it is about.
            # So we have to skip this field
            if stats_hero_class not in heroes_options:
                continue

            hero_key = get_hero_keyname(heroes_options[stats_hero_class])

            career_stats[hero_key] = []
            # Hero container children are div with "category" class
            for card_stat in hero_container.iter():
                # Content div should be the only child ("content" class)
                content_div = card_stat.first_child

                # Label should be the first div within content ("header" class)
                category_label = content_div.first_child.first_child.text()

                career_stats[hero_key].append(
                    {
                        "category": string_to_snakecase(category_label),
                        "label": category_label,
                        "stats": [],
                    },
                )
                for stat_row in content_div.iter():
                    if "stat-item" not in stat_row.attributes["class"]:
                        continue

                    stat_name = stat_row.first_child.text()
                    career_stats[hero_key][-1]["stats"].append(
                        {
                            "key": get_plural_stat_key(string_to_snakecase(stat_name)),
                            "label": stat_name,
                            "value": get_computed_stat_value(
                                stat_row.last_child.text()
                            ),
                        },
                    )

            # For a reason, sometimes the hero is in the dropdown but there
            # is no stat to show. In this case, return None as if there was
            # no stat at all
            if len(career_stats[hero_key]) == 0:
                del career_stats[hero_key]

        return career_stats

    @staticmethod
    def __get_heroes_options(
        parent_section: LexborNode, key_prefix: str = ""
    ) -> dict[str, str]:
        # Sometimes, pages are not rendered correctly and select can be empty
        if not (
            options := parent_section.css_first(
                "div.Profile-heroSummary--header > select"
            )
        ):
            return {}

        return {
            f"{key_prefix}{option.attributes['value']}": option.attributes["option-id"]
            for option in options.iter()
            if option.attributes.get("option-id")
        }
