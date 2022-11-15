"""Hero page Parser module"""

from bs4 import Tag

from overfastapi.common.enums import MediaType
from overfastapi.parsers.api_parser import APIParser
from overfastapi.parsers.helpers import get_full_url


class HeroParser(APIParser):
    """Overwatch single hero page Parser class"""

    def parse_data(self) -> dict:
        overview_section = self.root_tag.find("blz-page-header", recursive=False)
        abilities_section = self.root_tag.find(
            "div", class_="abilities-container", recursive=False
        )
        showcase_section = self.root_tag.find("blz-showcase", recursive=False)
        story_section = showcase_section.find("blz-header")

        return {
            **self.__get_summary(overview_section),
            "abilities": self.__get_abilities(abilities_section),
            "story": self.__get_story(story_section),
            "media": self.__get_media(showcase_section),
        }

    @staticmethod
    def __get_summary(overview_section: Tag) -> dict:
        header_section = overview_section.find("blz-header")
        extra_list_items = overview_section.find("blz-list").find_all("blz-list-item")
        return {
            "name": header_section.find("h2").get_text(),
            "description": header_section.find("p").get_text(),
            "role": extra_list_items[0].get_text().lower(),
            "location": extra_list_items[1].get_text(),
        }

    @staticmethod
    def __get_abilities(abilities_section: Tag) -> list[dict]:
        abilities_list_div = abilities_section.find(
            "blz-carousel-section", recursive=False
        ).find("blz-carousel", recursive=False)

        abilities_desc = [
            desc_div.find("blz-header").find("span").get_text()
            for desc_div in abilities_list_div.find_all("blz-feature")
        ]

        return [
            {
                "name": ability_div["label"],
                "description": abilities_desc[ability_index].strip(),
                "icon": ability_div.find("blz-image")["src"],
            }
            for ability_index, ability_div in enumerate(
                abilities_list_div.find("blz-tab-controls").find_all("blz-tab-control")
            )
        ]

    @staticmethod
    def __get_story(story_section: Tag) -> dict:
        return story_section.find("p").get_text()

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
