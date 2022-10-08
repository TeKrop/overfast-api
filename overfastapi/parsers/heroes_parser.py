"""Heroes page Parser module"""
from overfastapi.parsers.api_parser import APIParser


class HeroesParser(APIParser):
    """Overwatch heroes list page Parser class"""

    def parse_data(self) -> list:
        return [
            {
                "key": hero["data-hero-id"],
                "name": hero.find("div", class_="heroCardName").get_text(),
                "portrait": hero.find("blz-image")["src"],
                "role": hero["data-role"],
            }
            for hero in self.root_tag.find("blz-media-gallery").find_all(
                "blz-hero-card"
            )
        ]
