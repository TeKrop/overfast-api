"""List Roles Controller module"""

from typing import ClassVar

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.roles import parse_roles
from app.config import settings
from app.controllers import AbstractController
from app.enums import Locale
from app.exceptions import ParserParsingError
from app.helpers import overfast_internal_error


class ListRolesController(AbstractController):
    """List Roles Controller used in order to
    retrieve a list of available Overwatch roles.
    """

    parser_classes: ClassVar[list[type]] = []
    timeout = settings.heroes_path_cache_timeout

    async def process_request(self, **kwargs) -> list[dict]:
        """Process request using stateless parser function"""
        locale = kwargs.get("locale") or Locale.ENGLISH_US
        client = BlizzardClient()

        try:
            data = await parse_roles(client, locale=locale)
        except ParserParsingError as error:
            # Get Blizzard URL for error reporting
            blizzard_url = f"{settings.blizzard_host}/{locale}{settings.home_path}"
            raise overfast_internal_error(blizzard_url, error) from error

        # Dual-write to API Cache (Valkey) and Storage (SQLite)
        storage_key = f"roles:{locale}"
        await self.update_static_cache(data, storage_key, data_type="json")

        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
