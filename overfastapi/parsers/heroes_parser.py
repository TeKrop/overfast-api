"""Heroes page Parser module"""
from overfastapi.config import HEROES_PATH
from overfastapi.parsers.api_parser import APIParser


class HeroesParser(APIParser):
    """Overwatch heroes list page Parser class"""

    root_path = HEROES_PATH

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

    def filter_request_using_query(self, **kwargs) -> list[dict]:
        role = kwargs.get("role")
        return (
            self.data
            if not role
            else [hero_dict for hero_dict in self.data if hero_dict["role"] == role]
        )
