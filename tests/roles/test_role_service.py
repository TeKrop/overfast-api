"""Tests for RoleService — _parse error path and refresh_list"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, status

from app.domain.enums import Locale
from app.domain.exceptions import ParserParsingError
from app.domain.services.role_service import RoleService


def _make_role_service() -> RoleService:
    cache = AsyncMock()
    storage = AsyncMock()
    blizzard_client = AsyncMock()
    task_queue = AsyncMock()
    task_queue.is_job_pending_or_running.return_value = False
    return RoleService(cache, storage, blizzard_client, task_queue)


class TestRoleServiceParseError:
    def test_parse_raises_http_exception_on_parser_parsing_error(self):
        """If parse_roles_html raises ParserParsingError, _parse converts it to HTTPException."""
        svc = _make_role_service()
        config = svc._roles_config(Locale.ENGLISH_US, "/roles")
        parser = config.parser
        assert parser is not None

        with (
            patch(
                "app.domain.services.role_service.parse_roles_html",
                side_effect=ParserParsingError("bad HTML"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            parser("<bad-html>")

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestRoleServiceRefreshList:
    @pytest.mark.asyncio
    async def test_refresh_list_calls_fetch_and_store(self):
        """refresh_list() calls _fetch_and_store with the correct locale-based config."""
        svc = _make_role_service()

        with patch.object(svc, "_fetch_and_store", new=AsyncMock()) as mock_fetch_store:
            await svc.refresh_list(Locale.ENGLISH_US)

        mock_fetch_store.assert_awaited_once()
        # Verify the config passed has the correct storage_key
        call_args = mock_fetch_store.call_args[0][0]
        assert call_args.storage_key == "roles:en-us"

    @pytest.mark.asyncio
    async def test_refresh_list_cache_key_non_english(self):
        """Non-English locales include ?locale=XX in the cache key."""
        svc = _make_role_service()

        with patch.object(svc, "_fetch_and_store", new=AsyncMock()) as mock_fetch_store:
            await svc.refresh_list(Locale.FRENCH)

        call_args = mock_fetch_store.call_args[0][0]
        assert "fr-fr" in call_args.cache_key

    @pytest.mark.asyncio
    async def test_refresh_list_cache_key_english_us(self):
        """English US locale uses /roles as the cache key (no ?locale= suffix)."""
        svc = _make_role_service()

        with patch.object(svc, "_fetch_and_store", new=AsyncMock()) as mock_fetch_store:
            await svc.refresh_list(Locale.ENGLISH_US)

        call_args = mock_fetch_store.call_args[0][0]
        assert call_args.cache_key == "/roles"
