"""Roles Parser module"""

from app.config import settings
from app.parsers import HTMLParser

from ..helpers import get_role_from_icon_url


class RolesParser(HTMLParser):
    """Overwatch map gamemodes list page Parser class"""

    root_path = settings.home_path

    async def parse_data(self) -> list[dict]:
        roles_container = self.root_tag.css_first(
            "div.homepage-features-heroes blz-feature-carousel-section"
        )

        roles_icons = [
            role_icon_div.css_first("blz-image").attributes["src"]
            for role_icon_div in roles_container.css_first("blz-tab-controls").css(
                "blz-tab-control"
            )
        ]

        return [
            {
                "key": get_role_from_icon_url(roles_icons[role_index]),
                "name": role_div.css_first("blz-header h3").text().capitalize(),
                "icon": roles_icons[role_index],
                "description": (role_div.css_first("blz-header div").text().strip()),
            }
            for role_index, role_div in list(
                enumerate(roles_container.css("blz-feature"))
            )[:3]
        ]
