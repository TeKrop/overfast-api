"""PostgreSQL storage adapter with zstd compression for player profiles"""

from __future__ import annotations

import asyncio
import json
import time
from compression import zstd
from pathlib import Path
from typing import TYPE_CHECKING

import asyncpg

from app.config import settings
from app.metaclasses import Singleton
from app.monitoring.metrics import (
    storage_connection_errors_total,
    track_storage_operation,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports.storage import StaticDataCategory

_SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()


class PostgresStorage(metaclass=Singleton):
    """
    PostgreSQL storage adapter for persistent data.

    Provides persistent storage for:
    - Static data (heroes, maps, gamemodes, roles) as JSONB
    - Player profiles with zstd-compressed HTML

    Uses Singleton pattern to ensure a single connection pool across the application.
    """

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    @staticmethod
    async def _init_connection(conn: asyncpg.Connection) -> None:
        """Register JSON codec so JSONB columns accept/return Python dicts/lists."""
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    _MAX_POOL_CREATION_ATTEMPTS = 3

    async def initialize(self) -> None:
        """Create the connection pool and ensure schema exists."""
        async with self._init_lock:
            if self._initialized:
                return

            for attempt in range(1, self._MAX_POOL_CREATION_ATTEMPTS + 1):
                try:
                    self._pool = await asyncpg.create_pool(
                        dsn=settings.postgres_dsn,
                        min_size=settings.postgres_pool_min_size,
                        max_size=settings.postgres_pool_max_size,
                        init=self._init_connection,
                    )
                    break
                except Exception as exc:
                    if attempt == self._MAX_POOL_CREATION_ATTEMPTS:
                        if settings.prometheus_enabled:
                            storage_connection_errors_total.labels(
                                error_type="pool_creation"
                            ).inc()
                        logger.error(f"Failed to create PostgreSQL pool: {exc}")
                        raise
                    logger.warning(
                        f"PostgreSQL pool creation attempt {attempt}/{self._MAX_POOL_CREATION_ATTEMPTS}"
                        f" failed: {exc}. Retrying in 2s…"
                    )
                    await asyncio.sleep(2)

            await self._create_schema()
            self._initialized = True
            logger.info("PostgreSQL storage initialized")

    async def _create_schema(self) -> None:
        """Create enum type and tables if they don't exist."""
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(_SCHEMA_SQL)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Compression helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compress(data: str) -> bytes:
        return zstd.compress(data.encode("utf-8"))

    @staticmethod
    def _decompress(data: bytes) -> str:
        return zstd.decompress(data).decode("utf-8")

    # ------------------------------------------------------------------ #
    # Static data
    # ------------------------------------------------------------------ #

    @track_storage_operation("static_data", "get")
    async def get_static_data(self, key: str) -> dict | None:
        """Get static data by key. Returns dict with 'data', 'category',
        'updated_at' (Unix int), 'data_version' or None."""
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                """SELECT data, category, updated_at, data_version
                   FROM static_data WHERE key = $1""",
                key,
            )
        if row is None:
            return None
        return {
            "data": row["data"],
            "category": row["category"],
            "updated_at": int(row["updated_at"].timestamp()),
            "data_version": row["data_version"],
        }

    @track_storage_operation("static_data", "set")
    async def set_static_data(
        self,
        key: str,
        data: dict,
        category: StaticDataCategory,
        data_version: int = 1,
    ) -> None:
        """Upsert static data. ``data`` is stored as JSONB."""
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """INSERT INTO static_data (key, data, category, data_version, updated_at)
                   VALUES ($1, $2::jsonb, $3::static_data_category, $4, NOW())
                   ON CONFLICT (key) DO UPDATE
                   SET data = EXCLUDED.data,
                       category = EXCLUDED.category,
                       data_version = EXCLUDED.data_version,
                       updated_at = NOW()""",
                key,
                data,
                category.value,
                data_version,
            )

    # ------------------------------------------------------------------ #
    # Player profiles
    # ------------------------------------------------------------------ #

    @track_storage_operation("player_profiles", "get")
    async def get_player_profile(self, player_id: str) -> dict | None:
        """Get player profile by player_id.

        Returns dict with 'html', 'summary' (dict), 'battletag', 'name',
        'last_updated_blizzard', 'updated_at' (Unix int), 'data_version'
        or None if not found.
        """
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                """SELECT battletag, name, html_compressed, summary,
                          last_updated_blizzard, updated_at, data_version
                   FROM player_profiles WHERE player_id = $1""",
                player_id,
            )
        if row is None:
            return None

        summary = row["summary"] if row["summary"] is not None else {}
        if not summary:
            summary = {"url": player_id, "lastUpdated": row["last_updated_blizzard"]}

        return {
            "html": self._decompress(row["html_compressed"]),
            "battletag": row["battletag"],
            "name": row["name"],
            "summary": summary,
            "last_updated_blizzard": row["last_updated_blizzard"],
            "updated_at": int(row["updated_at"].timestamp()),
            "data_version": row["data_version"],
        }

    @track_storage_operation("player_profiles", "get")
    async def get_player_id_by_battletag(self, battletag: str) -> str | None:
        """Get Blizzard ID (player_id) for a given BattleTag."""
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                "SELECT player_id FROM player_profiles WHERE battletag = $1",
                battletag,
            )
        return row["player_id"] if row else None

    @track_storage_operation("player_profiles", "set")
    async def set_player_profile(
        self,
        player_id: str,
        html: str,
        summary: dict | None = None,
        battletag: str | None = None,
        name: str | None = None,
        last_updated_blizzard: int | None = None,
        data_version: int = 1,
    ) -> None:
        """Upsert player profile. HTML is zstd-compressed before storage."""
        if summary and last_updated_blizzard is None:
            last_updated_blizzard = summary.get("lastUpdated", last_updated_blizzard)

        compressed = self._compress(html)

        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """INSERT INTO player_profiles
                       (player_id, battletag, name, html_compressed, summary,
                        last_updated_blizzard, data_version, updated_at)
                   VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, NOW())
                   ON CONFLICT (player_id) DO UPDATE
                   SET battletag = COALESCE(EXCLUDED.battletag, player_profiles.battletag),
                       name = COALESCE(EXCLUDED.name, player_profiles.name),
                       html_compressed = EXCLUDED.html_compressed,
                       summary = EXCLUDED.summary,
                       last_updated_blizzard = EXCLUDED.last_updated_blizzard,
                       data_version = EXCLUDED.data_version,
                       updated_at = NOW()""",
                player_id,
                battletag,
                name,
                compressed,
                summary,
                last_updated_blizzard,
                data_version,
            )

    # ------------------------------------------------------------------ #
    # Maintenance
    # ------------------------------------------------------------------ #

    @track_storage_operation("player_profiles", "delete")
    async def delete_old_player_profiles(self, max_age_seconds: int) -> int:
        """Delete player profiles not updated within max_age_seconds.

        Returns:
            Number of deleted rows.
        """
        cutoff = time.time() - max_age_seconds
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            result = await conn.execute(
                "DELETE FROM player_profiles WHERE updated_at < TO_TIMESTAMP($1)",
                cutoff,
            )
        deleted = int(result.split()[-1])
        logger.info(
            f"Deleted {deleted} old player profiles (max_age={max_age_seconds}s)"
        )
        return deleted

    async def clear_all_data(self) -> None:
        """Truncate all tables (for testing)."""
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute("TRUNCATE static_data, player_profiles")

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #

    async def get_stats(self) -> dict:
        """Return storage statistics for monitoring."""
        stats: dict = {
            "size_bytes": 0,
            "static_data_count": 0,
            "player_profiles_count": 0,
            "player_profile_age_p50": 0,
            "player_profile_age_p90": 0,
            "player_profile_age_p99": 0,
        }
        try:
            async with self._pool.acquire() as conn:  # type: ignore[union-attr]
                row = await conn.fetchrow("SELECT COUNT(*) AS n FROM static_data")
                stats["static_data_count"] = row["n"]

                row = await conn.fetchrow("SELECT COUNT(*) AS n FROM player_profiles")
                stats["player_profiles_count"] = row["n"]

                # Approximate disk size via pg_total_relation_size
                row = await conn.fetchrow(
                    """SELECT pg_total_relation_size('player_profiles')
                            + pg_total_relation_size('static_data') AS total"""
                )
                stats["size_bytes"] = row["total"] or 0

                # Profile age percentiles
                ages = await conn.fetch(
                    """SELECT EXTRACT(EPOCH FROM (NOW() - updated_at)) AS age
                       FROM player_profiles
                       ORDER BY updated_at DESC
                       LIMIT 1000"""
                )
                if ages:
                    age_list = sorted(float(r["age"]) for r in ages)
                    n = len(age_list)
                    stats["player_profile_age_p50"] = age_list[n // 2]
                    stats["player_profile_age_p90"] = age_list[int(n * 0.9)]
                    stats["player_profile_age_p99"] = age_list[int(n * 0.99)]
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to collect storage stats: {exc}")

        return stats
