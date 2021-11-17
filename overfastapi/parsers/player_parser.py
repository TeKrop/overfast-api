"""Player profile page Parser module"""
from typing import Optional

from bs4 import Tag
from fastapi import status

from overfastapi.common.enums import CareerHeroesComparisonsCategory, HeroKey, Role
from overfastapi.common.exceptions import ParserInitError
from overfastapi.common.helpers import overfast_request
from overfastapi.config import BLIZZARD_HOST, SEARCH_ACCOUNT_PATH
from overfastapi.parsers.api_parser import APIParser
from overfastapi.parsers.helpers import (
    get_background_url_from_style,
    get_computed_stat_value,
    get_hero_keyname,
    string_to_snakecase,
)


class PlayerParser(APIParser):
    """Overwatch player profile page Parser class"""

    def __init__(self, html_content: str, **kwargs):
        super().__init__(html_content)
        self.player_id = kwargs.get("player_id")

        # We must check if we have expected section
        if not self.root_tag.find("section", id="overview-section"):
            raise ParserInitError(
                status_code=status.HTTP_404_NOT_FOUND, message="Player not found"
            )

    def parse_data(self) -> dict:
        overview_section = self.root_tag.find("section", id="overview-section")
        quickplay_section = self.root_tag.find("div", id="quickplay")
        competitive_section = self.root_tag.find("div", id="competitive")
        achievements_section = self.root_tag.find("section", id="achievements-section")

        return {
            "summary": self.__get_summary(overview_section),
            "quickplay": self.__get_gamemode_infos(quickplay_section),
            "competitive": self.__get_gamemode_infos(competitive_section),
            "achievements": self.__get_achievements(achievements_section),
        }

    def __get_summary(self, overview_section: Tag) -> dict:
        masthead_div = overview_section.find("div", class_="masthead-player")
        player_progression_div = masthead_div.find(
            "div", class_="masthead-player-progression", recursive=False
        )
        return {
            "username": masthead_div.find(
                "h1", class_="header-masthead", recursive=False
            ).get_text(),
            "avatar": masthead_div.find(
                "img", class_="player-portrait", recursive=False
            )["src"],
            "level": self.__get_level_details(player_progression_div),
            "competitive": self.__get_competitive_skill_rating(player_progression_div),
            "endorsement": self.__get_endorsement(player_progression_div),
            "games_won": self.__get_games_won(overview_section),
            "platforms": self.__get_platforms(overview_section),
            "privacy": self.__get_privacy(overview_section),
        }

    def __get_level_details(self, player_progression_div: Tag) -> dict:
        player_level = self.__get_player_level(player_progression_div)
        level_div = player_progression_div.find("div", class_="player-level")
        rank_div = player_progression_div.find("div", class_="player-rank")

        return {
            "value": player_level,
            "border": (
                get_background_url_from_style(level_div["style"]) if level_div else None
            ),
            "rank": (
                get_background_url_from_style(rank_div["style"]) if rank_div else None
            ),
        }

    def __get_player_level(self, player_progression_div: Tag) -> int:
        if self.player_id:
            player_name = self.player_id.split("-")[0]
            result = overfast_request(
                f"{BLIZZARD_HOST}{SEARCH_ACCOUNT_PATH}/{player_name}"
            )
            if result.status_code == 200:
                matching_account = next(
                    (
                        account
                        for account in result.json()
                        if account["urlName"] == self.player_id
                    ),
                    None,
                )
                if matching_account:
                    return matching_account["level"]

        # If we got an error or nothing found using the URL, return the level on the page
        return int(
            player_progression_div.find("div", class_="player-level")
            .find("div", class_="u-vertical-center")
            .get_text()
        )

    @staticmethod
    def __get_competitive_skill_rating(
        player_progression_div: Tag,
    ) -> Optional[list[dict]]:
        competitive_rank_div = player_progression_div.find(
            "div", class_="competitive-rank", recursive=False
        )
        if not competitive_rank_div:
            return None

        competitive_sr = {
            rank_role.find("div", class_="competitive-rank-tier")[
                "data-ow-tooltip-text"
            ]
            .split(" ")[0]
            .lower(): {
                "role_icon": rank_role.find("img", class_="competitive-rank-role-icon")[
                    "src"
                ],
                "skill_rating": int(
                    rank_role.find("div", class_="competitive-rank-level").get_text()
                ),
                "tier_icon": rank_role.find("img", class_="competitive-rank-tier-icon")[
                    "src"
                ],
            }
            for rank_role in competitive_rank_div.find_all(
                "div", class_="competitive-rank-role", recursive=False
            )
        }

        for role in Role:
            if role.value not in competitive_sr:
                competitive_sr[role.value] = None

        return competitive_sr

    @staticmethod
    def __get_endorsement(player_progression_div: Tag) -> dict:
        endorsement_div = player_progression_div.find(
            "div", class_="EndorsementIcon-tooltip", recursive=False
        )
        endorsement_distribution = endorsement_div.find(
            "div", class_="EndorsementIcon-inner"
        )

        return {
            "level": int(
                endorsement_div.find(
                    "div", class_="u-center", recursive=False
                ).get_text()
            ),
            "frame": get_background_url_from_style(
                endorsement_div.find("div", class_="EndorsementIcon")["style"]
            ),
            "distribution": {
                endorsement_type: float(
                    (
                        endorsement_distribution.find(
                            "svg", class_=f"EndorsementIcon-border--{endorsement_type}"
                        )
                        or {}
                    ).get("data-value", 0)
                )
                for endorsement_type in ("shotcaller", "teammate", "sportsmanship")
            },
        }

    @staticmethod
    def __get_games_won(overview_section: Tag) -> int:
        masthead_detail = overview_section.find("p", class_="masthead-detail")
        return int(masthead_detail.get_text().split()[0]) if masthead_detail else None

    @staticmethod
    def __get_platforms(overview_section: Tag) -> list[str]:
        return [
            button["href"].split("/")[2]
            for button in overview_section.find(
                "div", class_="masthead-buttons"
            ).find_all("a", class_="button")
        ]

    @staticmethod
    def __get_privacy(overview_section: Tag) -> str:
        privacy = "unknown"
        permission_level = overview_section.find(
            "p", class_="masthead-permission-level-text"
        ).get_text()
        if "Public" in permission_level:
            privacy = "public"
        elif "Private" in permission_level:
            privacy = "private"
        return privacy

    def __get_gamemode_infos(self, gamemode_section: Tag) -> Optional[dict]:
        if not gamemode_section:
            return None

        career_sections = gamemode_section.find_all(
            "section", class_="career-section", recursive=False
        )
        return {
            "heroes_comparisons": self.__get_heroes_comparisons(
                career_sections[0].find("div", recursive=False)
            ),
            "career_stats": self.__get_career_stats(
                career_sections[1].find("div", recursive=False)
            ),
        }

    @staticmethod
    def __get_real_category_name(category_name: str) -> str:
        """Specific method used because Blizzard sometimes name their categories
        in singular or plural. Example : "Objective Kill" or "Objective Kills".
        In order to be more consistent, I forced categories in one form (plural).
        """
        singular_to_plural_mapping = {
            "Game Won": "Games Won",
            "Elimination per Life": "Eliminations per Life",
            "Objective Kill": "Objective Kills",
        }
        return singular_to_plural_mapping.get(category_name, category_name)

    def __get_heroes_comparisons(self, gamemode_section: Tag) -> dict:
        categories = {
            option["value"]: option["option-id"]
            for option in (
                gamemode_section.find("div", class_="m-bottom-items", recursive=False)
                .find("select", attrs={"data-group-id": "comparisons"})
                .find_all("option")
            )
        }

        heroes_comparisons = {
            string_to_snakecase(
                self.__get_real_category_name(categories[category["data-category-id"]])
            ): {
                "label": self.__get_real_category_name(
                    categories[category["data-category-id"]]
                ),
                "values": [
                    {
                        "hero": get_hero_keyname(
                            progress_bar.find(
                                "div", class_="ProgressBar-title"
                            ).get_text()
                        ),
                        "value": get_computed_stat_value(
                            progress_bar.find(
                                "div", class_="ProgressBar-description"
                            ).get_text()
                        ),
                    }
                    for progress_bar in category.find_all(
                        "div", class_="ProgressBar", recursive=False
                    )
                ],
            }
            for category in gamemode_section.find_all(
                "div", class_="progress-category", recursive=False
            )
            if category["data-category-id"] in categories
        }

        for category in CareerHeroesComparisonsCategory:
            if category.value not in heroes_comparisons:
                heroes_comparisons[category.value] = None

        return heroes_comparisons

    @staticmethod
    def __get_career_stats(gamemode_section: Tag) -> dict:
        categories = {
            option["value"]: option["option-id"]
            for option in (
                gamemode_section.find("div", class_="m-bottom-items", recursive=False)
                .find("select", attrs={"data-group-id": "stats"})
                .find_all("option")
            )
        }

        career_stats = {
            get_hero_keyname(categories[category["data-category-id"]]): [
                {
                    "category": string_to_snakecase(
                        card_stat.find("th", class_="DataTable-tableHeading")
                        .find("h5", class_="stat-title")
                        .get_text()
                    ),
                    "label": (
                        card_stat.find("th", class_="DataTable-tableHeading")
                        .find("h5", class_="stat-title")
                        .get_text()
                    ),
                    "stats": [
                        {
                            "key": string_to_snakecase(
                                stat_row.find_all("td", class_="DataTable-tableColumn")[
                                    0
                                ].get_text()
                            ),
                            "label": stat_row.find_all(
                                "td", class_="DataTable-tableColumn"
                            )[0].get_text(),
                            "value": get_computed_stat_value(
                                stat_row.find_all("td", class_="DataTable-tableColumn")[
                                    1
                                ].get_text()
                            ),
                        }
                        for stat_row in card_stat.find(
                            "tbody", class_="DataTable-tableBody"
                        ).find_all("tr", class_="DataTable-tableRow")
                    ],
                }
                for card_stat in category.find_all(
                    "div", class_="card-stat-block-container", recursive=False
                )
            ]
            for category in gamemode_section.find_all(
                "div", class_="js-stats", recursive=False
            )
            if category["data-category-id"] in categories
        }

        for hero_key in HeroKey:
            if hero_key.value not in career_stats:
                career_stats[hero_key.value] = None

        return career_stats

    @staticmethod
    def __get_achievements(achievements_section: Tag) -> Optional[dict]:
        if not achievements_section:
            return None

        return {
            category["data-category-id"]: [
                {
                    "title": card.find("div", class_="media-card-title").get_text(),
                    "description": card.find("p", class_="h6").get_text(),
                    "image": card.find("img", class_="media-card-fill")["src"],
                }
                for card in category.find("ul", recursive=False).find_all(
                    "div", class_="achievement-card-container"
                )
                if "m-disabled"
                not in card.find("div", class_="achievement-card")["class"]
            ]
            for category in achievements_section.find_all(
                "div", attrs={"data-group-id": "achievements"}
            )
        }
