"""List Heroes Controller module"""

from typing import ClassVar

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.heroes import parse_heroes
from app.config import settings
from app.controllers import AbstractController
from app.enums import Locale
from app.exceptions import ParserParsingError
from app.helpers import overfast_internal_error


class ListHeroesController(AbstractController):
    """List Heroes Controller used in order to
    retrieve a list of available Overwatch heroes.
    """

    # Keep parser_classes for backward compatibility, but it's no longer used
    parser_classes: ClassVar[list[type]] = []
    timeout = settings.heroes_path_cache_timeout

    async def process_request(self, **kwargs) -> list[dict]:
        """Process request using stateless parser function"""
        # Extract params
        role = kwargs.get("role")
        locale = kwargs.get("locale") or Locale.ENGLISH_US
        gamemode = kwargs.get("gamemode")

        # Use stateless parser function
        client = BlizzardClient()

        try:
            data = await parse_heroes(
                client, locale=locale, role=role, gamemode=gamemode
            )
        except ParserParsingError as error:
            # Get Blizzard URL for error reporting
            blizzard_url = f"{settings.blizzard_host}/{locale}{settings.heroes_path}"
            raise overfast_internal_error(blizzard_url, error) from error

        # Dual-write to API Cache (Valkey) and Storage (SQLite)
        storage_key = f"heroes:{locale}"
        await self.update_static_cache(data, storage_key, data_type="json")

        # Ensure response headers contains Cache TTL
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
