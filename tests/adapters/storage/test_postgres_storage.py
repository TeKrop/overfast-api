"""Unit tests for PostgresStorage adapter"""

from __future__ import annotations

import datetime
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.storage.postgres_storage import PostgresStorage
from app.domain.ports.storage import StaticDataCategory


def _make_connection(fetchrow_result=None, fetch_result=None):
    """Create a mock asyncpg connection."""
    conn = AsyncMock()
    conn.set_type_codec = AsyncMock()
    conn.execute = AsyncMock(return_value="DELETE 3")
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    return conn


def _make_pool(conn=None):
    """Create a mock asyncpg pool with acquire() context manager."""
    if conn is None:
        conn = _make_connection()
    pool = AsyncMock()
    pool.close = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool.acquire = _acquire
    return pool, conn


def _make_storage(pool=None) -> PostgresStorage:
    """Create a PostgresStorage with an injected mock pool."""
    storage = PostgresStorage()
    if pool is not None:
        storage._pool = pool
        storage._initialized = True
    return storage


# ---------------------------------------------------------------------------
# Compression helpers
# ---------------------------------------------------------------------------


class TestCompressionHelpers:
    def test_compress_decompress_roundtrip(self):
        text = "Hello, World! " * 100
        compressed = PostgresStorage._compress(text)

        assert isinstance(compressed, bytes)
        assert PostgresStorage._decompress(compressed) == text

    def test_compress_produces_smaller_output(self):
        text = "a" * 10000
        compressed = PostgresStorage._compress(text)

        assert len(compressed) < len(text)


# ---------------------------------------------------------------------------
# lifecycle — initialize and close
# ---------------------------------------------------------------------------


class TestInitialize:
    @pytest.mark.asyncio
    async def test_initializes_pool_and_schema(self):
        pool, conn = _make_pool()
        with (
            patch(
                "app.adapters.storage.postgres_storage.asyncpg.create_pool",
                new_callable=AsyncMock,
                return_value=pool,
            ),
            patch("app.adapters.storage.postgres_storage.settings") as s,
        ):
            s.postgres_dsn = "postgresql://localhost/test"
            s.postgres_pool_min_size = 1
            s.postgres_pool_max_size = 5
            s.prometheus_enabled = False
            storage = PostgresStorage()
            await storage.initialize()

        assert storage._initialized is True
        conn.execute.assert_awaited()  # schema creation

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Calling initialize twice is a no-op (lock + _initialized guard)."""
        pool, _conn = _make_pool()
        with patch(
            "app.adapters.storage.postgres_storage.asyncpg.create_pool",
            new_callable=AsyncMock,
            return_value=pool,
        ) as mock_create:
            with patch("app.adapters.storage.postgres_storage.settings") as s:
                s.postgres_dsn = "postgresql://localhost/test"
                s.postgres_pool_min_size = 1
                s.postgres_pool_max_size = 5
                s.prometheus_enabled = False
                storage = PostgresStorage()
                await storage.initialize()
                await storage.initialize()
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_pool_creation_failure_raises(self):
        """Pool creation failure after max retries raises the exception."""
        with (
            patch(
                "app.adapters.storage.postgres_storage.asyncpg.create_pool",
                new_callable=AsyncMock,
                side_effect=OSError("connection refused"),
            ),
            patch(
                "app.adapters.storage.postgres_storage.asyncio.sleep",
                new_callable=AsyncMock,
            ),
            patch("app.adapters.storage.postgres_storage.settings") as s,
        ):
            s.postgres_dsn = "postgresql://localhost/test"
            s.postgres_pool_min_size = 1
            s.postgres_pool_max_size = 5
            s.prometheus_enabled = False
            storage = PostgresStorage()
            with pytest.raises(OSError, match="connection refused"):
                await storage.initialize()

    @pytest.mark.asyncio
    async def test_close_clears_pool(self):
        pool, _ = _make_pool()
        storage = _make_storage(pool=pool)
        await storage.close()

        pool.close.assert_awaited_once()
        assert storage._initialized is False


# ---------------------------------------------------------------------------
# get_static_data
# ---------------------------------------------------------------------------


class TestGetStaticData:
    @pytest.mark.asyncio
    async def test_returns_none_when_row_missing(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        storage = _make_storage(pool=pool)
        result = await storage.get_static_data("heroes")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_decompressed_data(self):
        payload = json.dumps({"heroes": []})
        compressed = PostgresStorage._compress(payload)
        updated_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
        row = {
            "data": compressed,
            "category": "heroes",
            "updated_at": updated_at,
            "data_version": 1,
        }
        conn = _make_connection()
        conn.fetchrow = AsyncMock(return_value=row)
        pool, _ = _make_pool(conn=conn)
        storage = _make_storage(pool=pool)
        result = await storage.get_static_data("heroes")

        assert result is not None
        assert result["data"] == payload
        assert result["category"] == "heroes"
        assert result["data_version"] == 1
        assert isinstance(result["updated_at"], int)


# ---------------------------------------------------------------------------
# set_static_data
# ---------------------------------------------------------------------------


class TestSetStaticData:
    @pytest.mark.asyncio
    async def test_compresses_and_upserts(self):
        pool, conn = _make_pool()
        storage = _make_storage(pool=pool)
        await storage.set_static_data(
            key="heroes",
            data='{"heroes": []}',
            category=StaticDataCategory.HEROES,
            data_version=2,
        )
        conn.execute.assert_awaited_once()
        args = conn.execute.call_args[0]

        # Second arg should be compressed bytes
        assert isinstance(args[2], bytes)


# ---------------------------------------------------------------------------
# get_player_profile
# ---------------------------------------------------------------------------


class TestGetPlayerProfile:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        storage = _make_storage(pool=pool)
        result = await storage.get_player_profile("nobody-0000")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_profile_with_summary(self):
        html = "<html>player</html>"
        compressed = PostgresStorage._compress(html)
        summary = {"url": "abc123", "lastUpdated": 1700000000}
        updated_at = datetime.datetime(2025, 6, 1, tzinfo=datetime.UTC)
        row = {
            "html_compressed": compressed,
            "battletag": "TeKrop-2217",
            "name": "TeKrop",
            "summary": summary,
            "last_updated_blizzard": 1700000000,
            "updated_at": updated_at,
            "data_version": 1,
        }
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=row)
        storage = _make_storage(pool=pool)
        result = await storage.get_player_profile("abc123")

        assert result is not None
        assert result["html"] == html
        assert result["summary"] == summary
        assert result["battletag"] == "TeKrop-2217"

    @pytest.mark.asyncio
    async def test_builds_summary_when_none(self):
        """When row summary is None, builds a minimal summary dict."""
        html = "<html>player</html>"
        compressed = PostgresStorage._compress(html)
        updated_at = datetime.datetime(2025, 6, 1, tzinfo=datetime.UTC)
        row = {
            "html_compressed": compressed,
            "battletag": None,
            "name": None,
            "summary": None,
            "last_updated_blizzard": 12345,
            "updated_at": updated_at,
            "data_version": 1,
        }
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=row)
        storage = _make_storage(pool=pool)
        result = await storage.get_player_profile("abc123")

        assert result is not None
        assert result["summary"]["url"] == "abc123"
        assert result["summary"]["lastUpdated"] == 12345  # noqa: PLR2004


# ---------------------------------------------------------------------------
# get_player_id_by_battletag
# ---------------------------------------------------------------------------


class TestGetPlayerIdByBattletag:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        storage = _make_storage(pool=pool)
        result = await storage.get_player_id_by_battletag("Unknown-9999")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_player_id(self):
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value={"player_id": "abc123|def456"})
        storage = _make_storage(pool=pool)
        result = await storage.get_player_id_by_battletag("TeKrop-2217")

        assert result == "abc123|def456"


# ---------------------------------------------------------------------------
# set_player_profile
# ---------------------------------------------------------------------------


class TestSetPlayerProfile:
    @pytest.mark.asyncio
    async def test_compresses_html_and_upserts(self):
        pool, conn = _make_pool()
        storage = _make_storage(pool=pool)
        await storage.set_player_profile(
            player_id="abc123",
            html="<html>player</html>",
            summary={"lastUpdated": 123},
            battletag="TeKrop-2217",
            name="TeKrop",
        )
        conn.execute.assert_awaited_once()
        args = conn.execute.call_args[0]

        # html_compressed is 4th positional arg
        assert isinstance(args[4], bytes)

    @pytest.mark.asyncio
    async def test_extracts_last_updated_from_summary(self):
        pool, conn = _make_pool()
        storage = _make_storage(pool=pool)
        await storage.set_player_profile(
            player_id="abc123",
            html="<html/>",
            summary={"lastUpdated": 9999},
        )
        args = conn.execute.call_args[0]

        # last_updated_blizzard is 6th positional arg
        assert args[6] == 9999  # noqa: PLR2004


# ---------------------------------------------------------------------------
# delete_old_player_profiles
# ---------------------------------------------------------------------------


class TestDeleteOldPlayerProfiles:
    @pytest.mark.asyncio
    async def test_returns_deleted_count(self):
        pool, conn = _make_pool()
        conn.execute = AsyncMock(return_value="DELETE 5")
        storage = _make_storage(pool=pool)
        result = await storage.delete_old_player_profiles(86400)

        assert result == 5  # noqa: PLR2004


# ---------------------------------------------------------------------------
# clear_all_data
# ---------------------------------------------------------------------------


class TestClearAllData:
    @pytest.mark.asyncio
    async def test_executes_truncate(self):
        pool, conn = _make_pool()
        storage = _make_storage(pool=pool)
        await storage.clear_all_data()

        conn.execute.assert_awaited_once()
        sql = conn.execute.call_args[0][0]
        assert "TRUNCATE" in sql


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    @pytest.mark.asyncio
    async def test_returns_stats_with_profiles(self):
        pool, conn = _make_pool()
        # Set up multiple fetchrow/fetch calls
        fetchrow_calls = [
            {"n": 5},  # static_data COUNT
            {"n": 10},  # player_profiles COUNT
            {"total": 1024000},  # size
        ]
        call_count = {"i": 0}

        async def fetchrow_side_effect(*_args, **_kwargs):
            result = fetchrow_calls[call_count["i"]]
            call_count["i"] += 1
            return result

        conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
        # Profile age rows
        conn.fetch = AsyncMock(
            return_value=[{"age": float(i * 100)} for i in range(10)]
        )
        storage = _make_storage(pool=pool)
        result = await storage.get_stats()

        _expected_static = 5
        _expected_profiles = 10
        _expected_size = 1024000
        assert result["static_data_count"] == _expected_static
        assert result["player_profiles_count"] == _expected_profiles
        assert result["size_bytes"] == _expected_size
        assert result["player_profile_age_p50"] > 0

    @pytest.mark.asyncio
    async def test_returns_zeroes_when_no_profiles(self):
        pool, conn = _make_pool()
        fetchrow_calls = [{"n": 0}, {"n": 0}, {"total": 0}]
        call_count = {"i": 0}

        async def fetchrow_side_effect(*_args, **_kwargs):
            result = fetchrow_calls[call_count["i"]]
            call_count["i"] += 1
            return result

        conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
        conn.fetch = AsyncMock(return_value=[])
        storage = _make_storage(pool=pool)
        result = await storage.get_stats()

        assert result["player_profile_age_p50"] == 0
        assert result["player_profile_age_p99"] == 0

    @pytest.mark.asyncio
    async def test_exception_returns_zeroed_stats(self):
        """DB errors are swallowed and return zeroed stats."""
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(side_effect=OSError("DB gone"))
        storage = _make_storage(pool=pool)
        result = await storage.get_stats()

        assert result["static_data_count"] == 0
        assert result["size_bytes"] == 0


# ---------------------------------------------------------------------------
# _init_connection
# ---------------------------------------------------------------------------


class TestInitConnection:
    @pytest.mark.asyncio
    async def test_registers_jsonb_codec(self):
        conn = AsyncMock()
        await PostgresStorage._init_connection(conn)

        conn.set_type_codec.assert_awaited_once_with(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
