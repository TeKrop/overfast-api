"""Heroes page Parser module"""

from app.config import settings
from app.parsers import HTMLParser


class HeroesParser(HTMLParser):
    """Overwatch heroes list page Parser class"""

    root_path = settings.heroes_path

    def parse_data(self) -> list[dict]:
        return sorted(
            [
                {
                    "key": hero["data-hero-id"],
                    "name": hero["hero-name"],
                    "portrait": hero.find("blz-image")["src"],
                    "role": hero["data-role"],
                }
                for hero in self.root_tag.find("blz-media-gallery").find_all(
                    "blz-hero-card",
                )
            ],
            key=lambda hero: hero["key"],
        )

    def filter_request_using_query(self, **kwargs) -> list[dict]:
        role = kwargs.get("role")
        return (
            self.data
            if not role
            else [hero_dict for hero_dict in self.data if hero_dict["role"] == role]
        )
