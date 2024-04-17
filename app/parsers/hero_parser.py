"""Hero page Parser module"""

from typing import ClassVar

from bs4 import Tag
from fastapi import status

from app.common.enums import Locale, MediaType
from app.common.exceptions import ParserBlizzardError
from app.config import settings

from .generics.api_parser import APIParser
from .helpers import get_birthday_and_age, get_full_url, get_role_from_icon_url


class HeroParser(APIParser):
    """Overwatch single hero page Parser class"""

    root_path = settings.heroes_path
    timeout = settings.hero_path_cache_timeout
    valid_http_codes: ClassVar[list] = [
        200,  # Classic response
        404,  # Hero Not Found response, we want to handle it here
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.locale = kwargs.get("locale") or Locale.ENGLISH_US

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{super().get_blizzard_url(**kwargs)}/{kwargs.get('hero_key')}"

    def parse_data(self) -> dict:
        # We must check if we have the expected section for hero. If not,
        # it means the hero hasn't been found and/or released yet.
        if not self.root_tag.find("div", class_="abilities-container", recursive=False):
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Hero not found or not released yet",
            )

        overview_section = self.root_tag.find("blz-page-header", recursive=False)
        abilities_section = self.root_tag.find(
            "div",
            class_="abilities-container",
            recursive=False,
        )
        lore_section = self.root_tag.find("blz-section", class_="lore", recursive=False)

        return {
            **self.__get_summary(overview_section),
            "abilities": self.__get_abilities(abilities_section),
            "story": self.__get_story(lore_section),
        }

    def __get_summary(self, overview_section: Tag) -> dict:
        header_section = overview_section.find("blz-header")
        extra_list_items = overview_section.find("blz-list").find_all("blz-list-item")
        birthday, age = get_birthday_and_age(
            text=extra_list_items[2].get_text(), locale=self.locale
        )

        return {
            "name": header_section.find("h2").get_text(),
            "description": (
                header_section.find("p", slot="description").get_text().strip()
            ),
            "role": get_role_from_icon_url(extra_list_items[0].find("image")["href"]),
            "location": extra_list_items[1].get_text(),
            "birthday": birthday,
            "age": age,
        }

    @staticmethod
    def __get_abilities(abilities_section: Tag) -> list[dict]:
        abilities_list_div = abilities_section.find(
            "blz-carousel-section",
            recursive=False,
        ).find("blz-carousel", recursive=False)

        abilities_desc = [
            (
                desc_div.find("blz-header")
                .find("span")
                .get_text()
                .strip()
                .replace("\r", "")
                .replace("\n", " ")
            )
            for desc_div in abilities_list_div.find_all("blz-feature")
        ]

        abilities_videos = [
            {
                "thumbnail": video_div["poster"],
                "link": {
                    "mp4": video_div["mp4"],
                    "webm": video_div["webm"],
                },
            }
            for video_div in abilities_section.find(
                "blz-carousel-section",
                recursive=False,
            ).find_all("blz-video", recursive=False)
        ]

        return [
            {
                "name": ability_div["label"],
                "description": abilities_desc[ability_index].strip(),
                "icon": ability_div.find("blz-image")["src"],
                "video": abilities_videos[ability_index],
            }
            for ability_index, ability_div in enumerate(
                abilities_list_div.find("blz-tab-controls").find_all("blz-tab-control"),
            )
        ]

    def __get_story(self, lore_section: Tag) -> dict:
        showcase_section = lore_section.find("blz-showcase", recursive=False)

        return {
            "summary": (
                showcase_section.find("blz-header")
                .find("p")
                .get_text()
                .strip()
                .replace("\n", "")
            ),
            "media": self.__get_media(showcase_section),
            "chapters": self.__get_story_chapters(
                lore_section.find("blz-accordion-section", recursive=False).find(
                    "blz-accordion",
                    recursive=False,
                ),
            ),
        }

    @staticmethod
    def __get_media(showcase_section: Tag) -> dict | None:
        if video := showcase_section.find("blz-video"):
            return {
                "type": MediaType.VIDEO,
                "link": f"https://youtu.be/{video['youtube-id']}",
            }

        if button := showcase_section.find("blz-button"):
            return {
                "type": (
                    MediaType.SHORT_STORY
                    if button["analytics-label"] == "short-story"
                    else MediaType.COMIC
                ),
                "link": get_full_url(button["href"]),
            }

        return None

    @staticmethod
    def __get_story_chapters(accordion: Tag) -> list[dict]:
        chapters_content = [
            (
                " ".join(
                    [
                        paragraph.get_text()
                        for paragraph in content_container.find_all("p")
                    ],
                ).strip()
            )
            for content_container in accordion.find_all(
                "div",
                slot="content",
                recursive=False,
            )
        ]
        chapters_picture = [
            picture["src"] for picture in accordion.find_all("blz-image")
        ]

        return [
            {
                "title": title_span.get_text().capitalize().strip(),
                "content": chapters_content[title_index],
                "picture": chapters_picture[title_index],
            }
            for title_index, title_span in enumerate(
                accordion.find_all("span", recursive=False),
            )
        ]
