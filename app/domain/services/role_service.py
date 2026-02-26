"""Role domain service — roles list"""

from app.adapters.blizzard.parsers.roles import fetch_roles_html, parse_roles_html
from app.config import settings
from app.domain.services.static_data_service import StaticDataService, StaticFetchConfig
from app.enums import Locale
from app.exceptions import ParserParsingError
from app.helpers import overfast_internal_error


class RoleService(StaticDataService):
    """Domain service for role data."""

    def _roles_config(self, locale: Locale, cache_key: str) -> StaticFetchConfig:
        """Build a StaticFetchConfig for the roles list."""

        async def _fetch() -> str:
            return await fetch_roles_html(self.blizzard_client, locale)

        def _parse(html: str) -> list[dict]:
            try:
                return parse_roles_html(html)
            except ParserParsingError as exc:
                blizzard_url = f"{settings.blizzard_host}/{locale}{settings.home_path}"
                raise overfast_internal_error(blizzard_url, exc) from exc

        return StaticFetchConfig(
            storage_key=f"roles:{locale}",
            fetcher=_fetch,
            parser=_parse,
            cache_key=cache_key,
            cache_ttl=settings.heroes_path_cache_timeout,
            staleness_threshold=settings.roles_staleness_threshold,
            entity_type="roles",
        )

    async def list_roles(
        self,
        locale: Locale,
        cache_key: str,
    ) -> tuple[list[dict], bool, int]:
        """Return the roles list.

        Stores raw Blizzard HTML per locale so that parser changes take effect
        on the next request after restart.
        """
        return await self.get_or_fetch(self._roles_config(locale, cache_key))

    async def refresh_list(self, locale: Locale) -> None:
        """Fetch fresh roles list, persist to storage and update API cache.

        Called by the background worker — bypasses the SWR layer.
        """
        locale_str = locale.value
        cache_key = (
            f"/roles?locale={locale_str}"
            if locale != Locale.ENGLISH_US
            else "/roles"
        )
        await self._fetch_and_store(self._roles_config(locale, cache_key))
