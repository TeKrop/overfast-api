"""List Maps Controller module"""

from typing import ClassVar

from app.adapters.blizzard.parsers.maps import parse_maps
from app.config import settings
from app.controllers import AbstractController


class ListMapsController(AbstractController):
    """List Maps Controller used in order to retrieve a list of
    available Overwatch maps.
    """

    parser_classes: ClassVar[list[type]] = []
    timeout = settings.csv_cache_timeout

    async def process_request(self, **kwargs) -> list[dict]:
        """Process request using stateless parser function"""
        gamemode = kwargs.get("gamemode")
        data = parse_maps(gamemode=gamemode)

        # Dual-write to API Cache (Valkey) and Storage (SQLite)
        storage_key = "maps:en-us"  # Maps are not localized
        await self.update_static_cache(data, storage_key, data_type="json")

        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
