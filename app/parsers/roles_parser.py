"""Roles Parser module"""
from app.config import settings

from .api_parser import APIParser
from .helpers import get_role_from_icon_url


class RolesParser(APIParser):
    """Overwatch map gamemodes list page Parser class"""

    root_path = settings.home_path
    timeout = settings.heroes_path_cache_timeout

    def parse_data(self) -> list[dict]:
        roles_container = self.root_tag.find(
            "div",
            class_="homepage-features-heroes",
            recursive=False,
        ).find("blz-feature-carousel-section", recursive=False)

        roles_icons = [
            role_icon_div.find("blz-image")["src:min-plus"]
            for role_icon_div in roles_container.find("blz-tab-controls").find_all(
                "blz-tab-control",
            )
        ]

        return [
            {
                "key": get_role_from_icon_url(roles_icons[role_index]),
                "name": role_div.find("blz-header").find("h2").get_text().capitalize(),
                "icon": roles_icons[role_index],
                "description": (
                    role_div.find("blz-header").find("div").get_text().strip()
                ),
            }
            for role_index, role_div in list(
                enumerate(roles_container.find_all("blz-feature")),
            )[:3]
        ]
