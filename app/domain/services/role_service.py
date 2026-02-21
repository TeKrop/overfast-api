"""Role domain service — roles list"""

from app.adapters.blizzard.parsers.roles import fetch_roles_html, parse_roles_html
from app.config import settings
from app.domain.services.base_service import BaseService
from app.enums import Locale
from app.exceptions import ParserParsingError
from app.helpers import overfast_internal_error


class RoleService(BaseService):
    """Domain service for role data."""

    async def list_roles(
        self,
        locale: Locale,
        cache_key: str,
    ) -> tuple[list[dict], bool]:
        """Return the roles list."""

        async def _fetch() -> list[dict]:
            try:
                html = await fetch_roles_html(self.blizzard_client, locale)  # ty: ignore[invalid-argument-type]
                return parse_roles_html(html)
            except ParserParsingError as exc:
                blizzard_url = f"{settings.blizzard_host}/{locale}{settings.home_path}"
                raise overfast_internal_error(blizzard_url, exc) from exc

        return await self.get_or_fetch(
            storage_key=f"roles:{locale}",
            fetcher=_fetch,
            cache_key=cache_key,
            cache_ttl=settings.heroes_path_cache_timeout,
            staleness_threshold=settings.roles_staleness_threshold,
            entity_type="roles",
        )
