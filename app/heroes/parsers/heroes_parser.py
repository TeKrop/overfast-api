"""Heroes page Parser module"""

from typing import cast

from app.config import settings
from app.exceptions import ParserParsingError
from app.parsers import HTMLParser


class HeroesParser(HTMLParser):
    """Overwatch heroes list page Parser class"""

    root_path = settings.heroes_path

    async def parse_data(self) -> list[dict]:
        heroes = []
        for hero in self.root_tag.css("div.heroIndexWrapper blz-media-gallery a"):
            if not hero.attributes["href"]:
                msg = "Invalid hero URL"
                raise ParserParsingError(msg)
            heroes.append(
                {
                    "key": hero.attributes["href"].split("/")[-1],
                    "name": hero.css_first("blz-card blz-content-block h2").text(),
                    "portrait": hero.css_first("blz-card blz-image").attributes["src"],
                    "role": hero.attributes["data-role"],
                }
            )

        return sorted(heroes, key=lambda hero: hero["key"])

    def filter_request_using_query(self, **kwargs) -> list[dict]:
        # Type assertion: we know parse_data returns list[dict]
        data = cast("list[dict]", self.data)
        role = kwargs.get("role")
        return (
            data
            if not role
            else [hero_dict for hero_dict in data if hero_dict["role"] == role]
        )
