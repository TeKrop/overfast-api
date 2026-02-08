"""Hero Stats Summary Controller module"""

from typing import ClassVar

from fastapi import HTTPException

from app.adapters.blizzard import BlizzardClient
from app.adapters.blizzard.parsers.hero_stats_summary import parse_hero_stats_summary
from app.config import settings
from app.controllers import AbstractController
from app.exceptions import ParserBlizzardError


class GetHeroStatsSummaryController(AbstractController):
    """Get Hero Stats Summary Controller used in order to
    retrieve usage statistics for Overwatch heroes.
    """

    parser_classes: ClassVar[list[type]] = []
    timeout = settings.hero_stats_cache_timeout

    async def process_request(self, **kwargs) -> list[dict]:
        """Process request using stateless parser function"""
        client = BlizzardClient()

        try:
            data = await parse_hero_stats_summary(
                client,
                platform=kwargs["platform"],
                gamemode=kwargs["gamemode"],
                region=kwargs["region"],
                role=kwargs.get("role"),
                map_filter=kwargs.get("map"),
                competitive_division=kwargs.get("competitive_division"),
                order_by=kwargs.get("order_by", "hero:asc"),
            )
        except ParserBlizzardError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail=error.message,
            ) from error

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        return data
