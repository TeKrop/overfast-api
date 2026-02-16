"""SQLite storage adapter with zstd compression"""

import json
import time
from compression import zstd
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

from app.config import settings
from app.metaclasses import Singleton
from app.monitoring.metrics import (
    sqlite_connection_errors_total,
    track_sqlite_operation,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Constants
MEMORY_DB = ":memory:"  # Special SQLite path for in-memory database


class SQLiteStorage(metaclass=Singleton):
    """
    SQLite storage adapter for persistent data with zstd compression.

    Provides persistent storage for:
    - Static data (heroes, maps, gamemodes, roles, hero_stats)
    - Player profiles (replaces Player Cache)
    - Player status tracking (replaces Unknown Players Cache with exponential backoff)

    All data is compressed with zstd (Python 3.14+ built-in) before storage.

    Uses Singleton pattern to ensure single instance across application.
    """

    def __init__(self, db_path: str | None = None):
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file. Defaults to settings.storage_path

        Note: Due to Singleton pattern, only first initialization sets db_path.
        For tests, use _reset_singleton() to create a fresh instance.
        """
        self.db_path = db_path or settings.storage_path
        self._initialized = False
        self._shared_connection: aiosqlite.Connection | None = (
            None  # For :memory: databases
        )

    @classmethod
    def _reset_singleton(cls):
        """Reset singleton instance (for testing only)"""
        instances = Singleton._instances  # noqa: SLF001
        if cls in instances:
            del instances[cls]

    @asynccontextmanager
    async def _get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Get a database connection with proper configuration.
        For :memory: databases, reuses a single connection to persist schema across operations.
        """
        try:
            # For in-memory databases, use a shared connection
            if self.db_path == MEMORY_DB:
                if self._shared_connection is None:
                    # Create and store the shared connection
                    db = await aiosqlite.connect(self.db_path)
                    await db.execute("PRAGMA journal_mode=WAL")

                    # Use NORMAL synchronous mode for better write performance
                    await db.execute("PRAGMA synchronous=NORMAL")

                    # Note: PRAGMA foreign_keys=ON removed - schema has no foreign key constraints
                    self._shared_connection = db
                yield self._shared_connection
                return

            # For file-based databases, create a new connection per operation
            async with aiosqlite.connect(self.db_path) as db:
                # Enable WAL mode for better concurrent read performance
                await db.execute("PRAGMA journal_mode=WAL")

                # Use NORMAL synchronous mode (safe with WAL mode, much faster writes)
                # Trade-off: Survives app crash, slight risk if OS crashes simultaneously
                # Acceptable for cache data that can be re-fetched from Blizzard
                await db.execute("PRAGMA synchronous=NORMAL")

                yield db
        except Exception as e:
            # Track connection errors
            if settings.prometheus_enabled:
                error_type = type(e).__name__
                sqlite_connection_errors_total.labels(error_type=error_type).inc()
            raise

    async def close(self) -> None:
        """Close the shared connection if it exists"""
        if self._shared_connection is not None:
            await self._shared_connection.close()
            self._shared_connection = None

    async def initialize(self) -> None:
        """Initialize database schema from schema.sql file"""
        if self._initialized:
            return

        # Ensure directory exists (skip for in-memory database)
        if self.db_path != MEMORY_DB:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Load schema from SQL file
        schema_path = Path(__file__).parent / "schema.sql"
        schema_sql = schema_path.read_text()

        async with self._get_connection() as db:
            # Execute schema (supports multiple statements)
            await db.executescript(schema_sql)
            await db.commit()

        self._initialized = True
        logger.info(f"SQLite storage initialized at {self.db_path}")

    def _compress(self, data: str) -> bytes:
        """Compress string data using zstd (module-level function for performance)"""
        return zstd.compress(data.encode("utf-8"))

    def _decompress(self, data: bytes) -> str:
        """Decompress zstd data to string (module-level function for performance)"""
        return zstd.decompress(data).decode("utf-8")

    # Static Data Methods

    @track_sqlite_operation("static_data", "get")
    async def get_static_data(self, key: str) -> dict | None:
        """
        Get static data by key.

        Returns:
            Dict with 'data', 'data_type', 'updated_at', 'schema_version' or None if not found
        """
        async with (
            self._get_connection() as db,
            db.execute(
                """SELECT data_type, data_compressed, updated_at, schema_version
                   FROM static_data WHERE key = ?""",
                (key,),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            if not row:
                return None

            return {
                "data_type": row[0],
                "data": self._decompress(row[1]),
                "updated_at": row[2],
                "schema_version": row[3],
            }

    @track_sqlite_operation("static_data", "set")
    async def set_static_data(
        self,
        key: str,
        data: str,
        data_type: str,
        schema_version: int = 1,
    ) -> None:
        """
        Store or update static data.

        Args:
            key: Unique key (e.g., "heroes:en-us", "hero_stats:pc:competitive:...")
            data: Raw HTML or JSON string
            data_type: "html" or "json"
            schema_version: Schema version for data format
        """
        now = int(time.time())
        compressed = self._compress(data)

        async with self._get_connection() as db:
            await db.execute(
                """INSERT OR REPLACE INTO static_data
                   (key, data_type, data_compressed, created_at, updated_at, schema_version)
                   VALUES (?, ?, ?, COALESCE((SELECT created_at FROM static_data WHERE key = ?), ?), ?, ?)""",
                (key, data_type, compressed, key, now, now, schema_version),
            )
            await db.commit()

    # Player Profile Methods

    @track_sqlite_operation("player_profiles", "get")
    async def get_player_profile(self, player_id: str) -> dict | None:
        """
        Get player profile by player_id (Blizzard ID).

        Args:
            player_id: Blizzard ID (canonical key)

        Returns:
            Dict with 'html', 'battletag', 'name', 'summary',
            'last_updated_blizzard', 'updated_at', 'schema_version' or None if not found
        """
        async with (
            self._get_connection() as db,
            db.execute(
                """SELECT battletag, name, html_compressed, summary_json,
                          last_updated_blizzard, updated_at, schema_version
                   FROM player_profiles WHERE player_id = ?""",
                (player_id,),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            if not row:
                return None

            # Parse summary_json if present, otherwise construct minimal summary
            summary = None
            if row[3]:  # summary_json column
                summary = json.loads(row[3])
            else:
                # Legacy entries without summary_json - construct minimal summary
                summary = {
                    "url": player_id,  # Use player_id (which IS the Blizzard ID)
                    "lastUpdated": row[4],  # last_updated_blizzard
                }

            return {
                "battletag": row[0],
                "name": row[1],
                "html": self._decompress(row[2]),
                "summary": summary,
                "last_updated_blizzard": row[4],
                "updated_at": row[5],
                "schema_version": row[6],
            }

    @track_sqlite_operation("player_profiles", "get")
    async def get_player_id_by_battletag(self, battletag: str) -> str | None:
        """
        Get Blizzard ID (player_id) for a given BattleTag.

        This enables lookup optimization: when a user provides a BattleTag we've seen before,
        we can skip the Blizzard redirect call and use the cached Blizzard ID directly.

        Args:
            battletag: BattleTag to lookup (e.g., "TeKrop-2217")

        Returns:
            Blizzard ID if found, None otherwise
        """
        async with (
            self._get_connection() as db,
            db.execute(
                "SELECT player_id FROM player_profiles WHERE battletag = ?",
                (battletag,),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            return row[0] if row else None

    @track_sqlite_operation("player_profiles", "set")
    async def set_player_profile(
        self,
        player_id: str,
        html: str,
        summary: dict | None = None,
        battletag: str | None = None,
        name: str | None = None,
        last_updated_blizzard: int | None = None,
        schema_version: int = 1,
    ) -> None:
        """
        Store or update player profile.

        Args:
            player_id: Blizzard ID (canonical key)
            html: Raw career page HTML
            summary: Full player summary from search endpoint (dict)
            battletag: Full BattleTag from user input (e.g., "TeKrop-2217"), optional
            name: Display name extracted from HTML or summary, optional
            last_updated_blizzard: Blizzard's lastUpdated (deprecated, use summary["lastUpdated"])
            schema_version: Schema version for parser format
        """
        now = int(time.time())
        compressed = self._compress(html)

        # If summary provided, extract lastUpdated and name from it
        if summary:
            last_updated_blizzard = summary.get("lastUpdated", last_updated_blizzard)
            # Extract name from summary if not provided
            if not name:
                name = summary.get("name")
            summary_json = json.dumps(summary)
        else:
            summary_json = None

        async with self._get_connection() as db:
            await db.execute(
                """INSERT OR REPLACE INTO player_profiles
                   (player_id, battletag, name, html_compressed, summary_json,
                    last_updated_blizzard, created_at, updated_at, schema_version)
                   VALUES (?, ?, ?, ?, ?, ?,
                           COALESCE((SELECT created_at FROM player_profiles WHERE player_id = ?), ?),
                           ?, ?)""",
                (
                    player_id,
                    battletag,
                    name,
                    compressed,
                    summary_json,
                    last_updated_blizzard,
                    player_id,
                    now,
                    now,
                    schema_version,
                ),
            )
            await db.commit()

    # Player Status Methods (Unknown Players with Exponential Backoff)

    @track_sqlite_operation("player_status", "get")
    async def get_player_status(self, player_id: str) -> dict | None:
        """
        Get player status for unknown player tracking by player_id OR battletag.

        Args:
            player_id: Blizzard ID or BattleTag to lookup

        Returns:
            Dict with 'check_count', 'last_checked_at', 'retry_after', 'battletag' or None if not found
        """
        async with (
            self._get_connection() as db,
            db.execute(
                """SELECT check_count, last_checked_at, retry_after, battletag
                   FROM player_status WHERE player_id = ? OR battletag = ?""",
                (player_id, player_id),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            if not row:
                return None

            return {
                "check_count": row[0],
                "last_checked_at": row[1],
                "retry_after": row[2],
                "battletag": row[3],
            }

    @track_sqlite_operation("player_status", "set")
    async def set_player_status(
        self,
        player_id: str,
        check_count: int,
        retry_after: int,
        battletag: str | None = None,
    ) -> None:
        """
        Set player status for unknown player tracking with exponential backoff.

        Args:
            player_id: Blizzard ID (canonical key)
            check_count: Number of failed checks
            retry_after: Seconds to wait before next check
            battletag: Optional BattleTag to enable early rejection of BattleTag requests
                      If None, preserves existing battletag value
        """
        now = int(time.time())

        async with self._get_connection() as db:
            if battletag:
                # New battletag provided - store it
                await db.execute(
                    """INSERT OR REPLACE INTO player_status
                       (player_id, battletag, check_count, last_checked_at, retry_after)
                       VALUES (?, ?, ?, ?, ?)""",
                    (player_id, battletag, check_count, now, retry_after),
                )
            else:
                # No battletag provided - preserve existing value
                await db.execute(
                    """INSERT INTO player_status
                       (player_id, battletag, check_count, last_checked_at, retry_after)
                       VALUES (?, NULL, ?, ?, ?)
                       ON CONFLICT(player_id) DO UPDATE SET
                           battletag = COALESCE(?, battletag),
                           check_count = excluded.check_count,
                           last_checked_at = excluded.last_checked_at,
                           retry_after = excluded.retry_after""",
                    (player_id, check_count, now, retry_after, battletag),
                )
            await db.commit()

    async def delete_player_status(self, player_id: str) -> None:
        """
        Delete player status entry (used when promoting unknown player to profile).

        Args:
            player_id: Player identifier
        """
        async with self._get_connection() as db:
            await db.execute(
                "DELETE FROM player_status WHERE player_id = ?", (player_id,)
            )
            await db.commit()

    # Maintenance & Metrics Methods

    async def get_stats(self) -> dict:
        """
        Get comprehensive storage statistics for Prometheus metrics.

        Phase 3.5B: Enhanced with detailed metrics including:
        - Row counts per table
        - Database and WAL file sizes
        - Compression ratios
        - Data freshness statistics
        - Per-table storage breakdown

        Returns:
            Dict with comprehensive storage metrics
        """
        stats = {}

        async with self._get_connection() as db:
            # Row counts per table
            async with db.execute("SELECT COUNT(*) FROM static_data") as cursor:
                row = await cursor.fetchone()
                stats["static_data_count"] = row[0] if row else 0

            async with db.execute("SELECT COUNT(*) FROM player_profiles") as cursor:
                row = await cursor.fetchone()
                stats["player_profiles_count"] = row[0] if row else 0

            async with db.execute("SELECT COUNT(*) FROM player_status") as cursor:
                row = await cursor.fetchone()
                stats["player_status_count"] = row[0] if row else 0

            # Data freshness (player profiles age distribution)
            current_time = int(time.time())
            async with db.execute(
                "SELECT updated_at FROM player_profiles ORDER BY updated_at DESC LIMIT 1000"
            ) as cursor:
                rows = await cursor.fetchall()
                if rows:
                    ages = [current_time - row[0] for row in rows if row[0]]
                    if ages:
                        ages.sort()
                        stats["player_profile_age_p50"] = ages[len(ages) // 2]
                        stats["player_profile_age_p90"] = ages[int(len(ages) * 0.9)]
                        stats["player_profile_age_p99"] = ages[int(len(ages) * 0.99)]
                    else:
                        stats["player_profile_age_p50"] = 0
                        stats["player_profile_age_p90"] = 0
                        stats["player_profile_age_p99"] = 0
                else:
                    stats["player_profile_age_p50"] = 0
                    stats["player_profile_age_p90"] = 0
                    stats["player_profile_age_p99"] = 0

        # File sizes
        if self.db_path == MEMORY_DB:
            # Estimate size for in-memory database
            stats["size_bytes"] = (
                (stats["static_data_count"] * 1024)
                + (stats["player_profiles_count"] * 10240)
                + (stats["player_status_count"] * 100)
            )
            stats["wal_size_bytes"] = 0
        else:
            db_file = Path(self.db_path)
            wal_file = Path(f"{self.db_path}-wal")

            stats["size_bytes"] = db_file.stat().st_size if db_file.exists() else 0
            stats["wal_size_bytes"] = (
                wal_file.stat().st_size if wal_file.exists() else 0
            )

        return stats

    async def clear_all_data(self) -> None:
        """Clear all data including static data (for testing)"""
        async with self._get_connection() as db:
            await db.execute("DELETE FROM static_data")
            await db.execute("DELETE FROM player_profiles")
            await db.execute("DELETE FROM player_status")
            await db.commit()

    async def optimize(self) -> None:
        """
        Run SQLite query optimizer to update statistics for query planner.

        This should be called:
        - On application shutdown
        - Periodically (e.g., hourly via background scheduler)
        - After bulk data operations

        The optimizer only analyzes tables that have changed significantly
        since last optimization, making it very lightweight (typically milliseconds).

        See: https://www.sqlite.org/pragma.html#pragma_optimize
        """
        async with self._get_connection() as db:
            await db.execute("PRAGMA optimize")
            await db.commit()
            logger.info("SQLite query optimizer executed successfully")
