"""Heroes page Parser module"""

from app.config import settings
from app.parsers import HTMLParser


class HeroesParser(HTMLParser):
    """Overwatch heroes list page Parser class"""

    root_path = settings.heroes_path

    async def parse_data(self) -> list[dict]:
        return sorted(
            [
                {
                    "key": hero.attributes["data-hero-id"],
                    "name": hero.attributes["hero-name"],
                    "portrait": hero.css_first("blz-image").attributes["src"],
                    "role": hero.attributes["data-role"],
                }
                for hero in self.root_tag.css("blz-media-gallery blz-hero-card")
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
