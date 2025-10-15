"""Hero page Parser module"""

import re
from typing import TYPE_CHECKING, ClassVar

from fastapi import status

from app.config import settings
from app.enums import Locale
from app.exceptions import ParserBlizzardError
from app.parsers import HTMLParser
from app.roles.helpers import get_role_from_icon_url

from ..enums import MediaType

if TYPE_CHECKING:
    from selectolax.lexbor import LexborNode


class HeroParser(HTMLParser):
    """Overwatch single hero page Parser class"""

    root_path = settings.heroes_path
    valid_http_codes: ClassVar[list] = [
        200,  # Classic response
        404,  # Hero Not Found response, we want to handle it here
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.locale = kwargs.get("locale") or Locale.ENGLISH_US

    def get_blizzard_url(self, **kwargs) -> str:
        return f"{super().get_blizzard_url(**kwargs)}{kwargs.get('hero_key')}/"

    async def parse_data(self) -> dict:
        # We must check if we have the expected section for hero. If not,
        # it means the hero hasn't been found and/or released yet.
        if not (
            abilities_section := self.root_tag.css_first("div.abilities-container")
        ):
            raise ParserBlizzardError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Hero not found or not released yet",
            )

        overview_section = self.root_tag.css_first("blz-page-header")
        lore_section = self.root_tag.css_first("blz-section.lore")

        return {
            **self.__get_summary(overview_section),
            "abilities": self.__get_abilities(abilities_section),
            "story": self.__get_story(lore_section),
        }

    def __get_summary(self, overview_section: LexborNode) -> dict:
        header_section = overview_section.css_first("blz-header")
        extra_list_items = overview_section.css_first("blz-list").css("blz-list-item")
        birthday, age = self.__get_birthday_and_age(
            text=extra_list_items[2].css_first("p").text(), locale=self.locale
        )

        return {
            "name": header_section.css_first("h2").text(),
            "description": header_section.css_first("p").text().strip(),
            "role": get_role_from_icon_url(
                extra_list_items[0].css_first("blz-icon").attributes["src"]
            ),
            "location": extra_list_items[1].text().strip(),
            "birthday": birthday,
            "age": age,
        }

    @staticmethod
    def __get_birthday_and_age(
        text: str, locale: Locale
    ) -> tuple[str | None, int | None]:
        """Get birthday and age from text for a given hero"""

        # Regex matching the birthday for every known locale
        birthday_regex = r"^(.*) [\(（].*[:：] ?(\d+).*[\)）]$"

        result = re.match(birthday_regex, text)
        if not result:
            return None, None

        # Text corresponding to "Unknown" in the locale of the page
        unknown_texts = {
            Locale.GERMAN: "Unbekannt",
            Locale.ENGLISH_EU: "Unknown",
            Locale.ENGLISH_US: "Unknown",
            Locale.SPANISH_EU: "Desconocido",
            Locale.SPANISH_LATIN: "Desconocido",
            Locale.FRENCH: "Inconnu",
            Locale.ITALIANO: "Sconosciuto",
            Locale.JAPANESE: "不明",
            Locale.KOREAN: "알 수 없음",
            Locale.POLISH: "Nieznane",
            Locale.PORTUGUESE_BRAZIL: "Desconhecido",
            Locale.RUSSIAN: "Неизвестно",
            Locale.CHINESE_TAIWAN: "未知",
        }
        unknown_text = unknown_texts.get(locale, "Unknown")

        birthday = result[1] if result[1] != unknown_text else None
        age = int(result[2]) if result[2] else None

        return birthday, age

    @staticmethod
    def __get_abilities(abilities_section: LexborNode) -> list[dict]:
        carousel_section_div = abilities_section.css_first("blz-carousel-section")
        abilities_list_div = carousel_section_div.css_first("blz-carousel")

        abilities_desc = [
            (
                desc_div.css_first("p")
                .text()
                .strip()
                .replace("\r", "")
                .replace("\n", " ")
            )
            for desc_div in abilities_list_div.css("blz-feature")
        ]

        abilities_videos = [
            {
                "thumbnail": video_div.attributes["poster"],
                "link": {
                    "mp4": video_div.attributes["mp4"],
                    "webm": video_div.attributes["webm"],
                },
            }
            for video_div in carousel_section_div.css("blz-web-video")
        ]

        return [
            {
                "name": ability_div.attributes["label"],
                "description": abilities_desc[ability_index].strip(),
                "icon": ability_div.css_first("blz-image").attributes["src"],
                "video": abilities_videos[ability_index],
            }
            for ability_index, ability_div in enumerate(
                abilities_list_div.css_first("blz-tab-controls").css("blz-tab-control"),
            )
        ]

    def __get_story(self, lore_section: LexborNode) -> dict:
        showcase_section = lore_section.css_first("blz-showcase")

        return {
            "summary": (
                showcase_section.css_first("blz-header p")
                .text()
                .strip()
                .replace("\n", "")
            ),
            "media": self.__get_media(showcase_section),
            "chapters": self.__get_story_chapters(
                lore_section.css_first("blz-accordion-section blz-accordion")
            ),
        }

    def __get_media(self, showcase_section: LexborNode) -> dict | None:
        if video := showcase_section.css_first("blz-youtube-video"):
            return {
                "type": MediaType.VIDEO,
                "link": f"https://youtu.be/{video.attributes['youtube-id']}",
            }

        if button := showcase_section.css_first("blz-button"):
            return {
                "type": (
                    MediaType.SHORT_STORY
                    if button.attributes["analytics-label"] == "short-story"
                    else MediaType.COMIC
                ),
                "link": self.__get_full_url(button.attributes["href"]),
            }

        return None

    @staticmethod
    def __get_full_url(url: str) -> str:
        """Get full URL from extracted URL. If URL begins with /, we use the
        blizzard host to get the full URL"""
        return f"{settings.blizzard_host}{url}" if url.startswith("/") else url

    @staticmethod
    def __get_story_chapters(accordion: LexborNode) -> list[dict]:
        chapters_content = [
            (
                " ".join(
                    [paragraph.text() for paragraph in content_container.css("p,pr")],
                ).strip()
            )
            for content_container in accordion.css("div[slot=content]")
        ]
        chapters_picture = [
            picture.attributes["src"] for picture in accordion.css("blz-image")
        ]
        titles = [node for node in accordion.iter() if node.tag == "span"]

        return [
            {
                "title": title_span.text().capitalize().strip(),
                "content": chapters_content[title_index],
                "picture": chapters_picture[title_index],
            }
            for title_index, title_span in enumerate(titles)
        ]
