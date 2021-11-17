"""Hero page Parser module"""
from bs4 import Tag

from overfastapi.parsers.api_parser import APIParser
from overfastapi.parsers.helpers import get_background_url_from_style, get_full_url


class HeroParser(APIParser):
    """Overwatch single hero page Parser class"""

    def parse_data(self) -> dict:
        abilities_section = self.root_tag.find(
            "section", id="abilities", recursive=False
        )
        details_section = self.root_tag.find("section", id="details", recursive=False)
        overview_section = details_section.find("section", id="overview")
        story_section = details_section.find("section", id="story")
        medias_section = self.root_tag.find("section", id="media")

        return {
            **self.__get_summary(abilities_section, overview_section),
            "weapons": self.__get_weapons(overview_section),
            "abilities": self.__get_abilities(overview_section),
            "story": self.__get_story(story_section),
            "medias": self.__get_medias(medias_section),
        }

    @staticmethod
    def __get_summary(abilities_section: Tag, overview_section: Tag) -> dict:
        return {
            "name": abilities_section.find("h1", class_="hero-name").get_text(),
            "role": (
                overview_section.find("h4", class_="hero-detail-role-name")
                .get_text()
                .lower()
            ),
            "difficulty": len(
                overview_section.find("div", class_="hero-detail-difficulty").select(
                    "span.star:not(.m-empty)"
                )
            ),
            "description": overview_section.find(
                "p", class_="hero-detail-description"
            ).get_text(),
        }

    def __get_weapons(self, overview_section: Tag) -> list[dict]:
        return [
            {
                "icon": weapon_div.find("img")["src"],
                "primary_fire": self.__get_primary_fire(weapon_div),
                "secondary_fire": self.__get_secondary_fire(weapon_div),
            }
            for weapon_div in overview_section.find(
                "div", class_="hero-detail-abilities weapons"
            ).find_all("div", class_="hero-ability")
        ]

    @staticmethod
    def __get_primary_fire(weapon_div: Tag) -> dict:
        weapon_abilities = weapon_div.find_all("div", class_="hero-ability-weapon")
        primary_fire_div = (
            weapon_abilities[0]
            if weapon_abilities
            else weapon_div.find("div", class_="hero-ability-descriptor")
        )
        return {
            "name": primary_fire_div.find("h4", class_="hero-ability-name").get_text(),
            "description": primary_fire_div.find(
                "p", class_="hero-ability-description"
            ).get_text(),
        }

    @staticmethod
    def __get_secondary_fire(weapon_div: Tag) -> dict | None:
        weapon_abilities = weapon_div.find_all("div", class_="hero-ability-weapon")
        return (
            {
                "name": (
                    weapon_abilities[1]
                    .find("h4", class_="hero-ability-name")
                    .get_text()
                ),
                "description": (
                    weapon_abilities[1]
                    .find("p", class_="hero-ability-description")
                    .get_text()
                ),
            }
            if weapon_abilities
            else None
        )

    @staticmethod
    def __get_abilities(overview_section: Tag) -> list[dict]:
        return [
            {
                "name": ability_div.find("h4", class_="hero-ability-name").get_text(),
                "description": ability_div.find(
                    "p", class_="hero-ability-description"
                ).get_text(),
                "icon": ability_div.find("img")["src"],
            }
            for ability_div in overview_section.find(
                "div", class_="hero-detail-abilities abilities"
            ).find_all("div", class_="hero-ability")
        ]

    def __get_story(self, story_section: Tag) -> dict:
        hero_bio = story_section.find("ul", class_="hero-bio")
        hero_name_and_age = (
            hero_bio.find("li", class_="name", recursive=False)
            .find("span", class_="hero-bio-copy", recursive=False)
            .get_text()
            .split(",")
        )

        return {
            "biography": {
                "real_name": hero_name_and_age[0],
                "age": hero_name_and_age[1].split(":")[1].strip(),
                "occupation": (
                    hero_bio.find("li", class_="occupation", recursive=False)
                    .find("span", class_="hero-bio-copy", recursive=False)
                    .get_text()
                    .split(":")[1]
                    .strip()
                ),
                "base_of_operations": (
                    hero_bio.find("li", class_="base", recursive=False)
                    .find("span", class_="hero-bio-copy", recursive=False)
                    .get_text()
                    .split(":")[1]
                    .strip()
                ),
                "affiliation": (
                    hero_bio.find("li", class_="affiliation", recursive=False)
                    .find("span", class_="hero-bio-copy", recursive=False)
                    .get_text()
                    .split(":")[1]
                    .strip()
                ),
            },
            "catch_phrase": self.__get_catch_phrase(story_section),
            "back_story": " ".join(
                [
                    paragraph.get_text()
                    for paragraph in story_section.find(
                        "div", class_="hero-bio-backstory"
                    ).find_all("p")
                ]
            ),
        }

    @staticmethod
    def __get_catch_phrase(story_section: Tag) -> dict | None:
        catch_phrase = story_section.find("p", class_="hero-bio-quote")
        return catch_phrase.get_text()[1:-1] if catch_phrase is not None else None

    @staticmethod
    def __get_medias(medias_section: Tag) -> list[dict]:
        return [
            {
                "title": media.find("h1", class_="Card-title").get_text(),
                "type": media.find("a", class_="CardLink", recursive=False)[
                    "data-type"
                ],
                "thumbnail": get_background_url_from_style(
                    media.find("div", class_="Card-thumbnail")["style"]
                ),
                "link": get_full_url(
                    media.find("a", class_="CardLink", recursive=False)["href"]
                ),
            }
            for media in medias_section.find("div", class_="MediaGallery").find_all(
                "div", class_="MediaItem", recursive=False
            )
        ]
