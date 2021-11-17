"""Heroes page Parser module"""
import json

from overfastapi.parsers.api_parser import APIParser


class HeroesParser(APIParser):
    """Overwatch heroes list page Parser class"""

    def parse_data(self) -> list:
        return [
            {
                "key": hero.find("a", class_="hero-portrait-detailed")["data-hero-id"],
                "name": hero.find("span", class_="portrait-title").get_text(),
                "portrait": hero.find("img", class_="portrait")["src"],
                "role": json.loads(hero["data-groups"])[0].lower(),
            }
            for hero in self.root_tag.find(
                "div", id="heroes-selector-container"
            ).find_all("div", class_="hero-portrait-detailed-container")
        ]

    @property
    def root_tag_params(self) -> dict:
        return {"name": "div", "id": "heroes-index"}
