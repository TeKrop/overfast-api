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
        # For in-memory databases, use a shared connection
        if self.db_path == MEMORY_DB:
            if self._shared_connection is None:
                # Create and store the shared connection
                db = await aiosqlite.connect(self.db_path)
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("PRAGMA foreign_keys=ON")
                self._shared_connection = db
            yield self._shared_connection
            return

        # For file-based databases, create a new connection per operation
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrent read performance
            await db.execute("PRAGMA journal_mode=WAL")
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys=ON")
            yield db

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

    async def get_player_profile(self, player_id: str) -> dict | None:
        """
        Get player profile by player_id.

        Returns:
            Dict with 'html', 'blizzard_id', 'summary', 'last_updated_blizzard',
            'updated_at', 'schema_version' or None if not found
        """
        async with (
            self._get_connection() as db,
            db.execute(
                """SELECT blizzard_id, html_compressed, summary_json, last_updated_blizzard,
                          updated_at, schema_version
                   FROM player_profiles WHERE player_id = ?""",
                (player_id,),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            if not row:
                return None

            # Parse summary_json if present, otherwise construct minimal summary
            summary = None
            if row[2]:  # summary_json column
                summary = json.loads(row[2])
            else:
                # Legacy entries without summary_json - construct minimal summary
                summary = {
                    "url": row[0],  # blizzard_id
                    "lastUpdated": row[3],  # last_updated_blizzard
                }

            return {
                "blizzard_id": row[0],
                "html": self._decompress(row[1]),
                "summary": summary,
                "last_updated_blizzard": row[3],
                "updated_at": row[4],
                "schema_version": row[5],
            }

    async def set_player_profile(
        self,
        player_id: str,
        html: str,
        summary: dict | None = None,
        blizzard_id: str | None = None,
        last_updated_blizzard: int | None = None,
        schema_version: int = 1,
    ) -> None:
        """
        Store or update player profile.

        Args:
            player_id: Player identifier (BattleTag)
            html: Raw career page HTML
            summary: Full player summary from search endpoint (dict)
            blizzard_id: Blizzard ID (deprecated, use summary["url"])
            last_updated_blizzard: Blizzard's lastUpdated (deprecated, use summary["lastUpdated"])
            schema_version: Schema version for parser format
        """
        now = int(time.time())
        compressed = self._compress(html)

        # If summary provided, extract blizzard_id and lastUpdated from it
        if summary:
            blizzard_id = summary.get("url", blizzard_id)
            last_updated_blizzard = summary.get("lastUpdated", last_updated_blizzard)
            summary_json = json.dumps(summary)
        else:
            summary_json = None

        async with self._get_connection() as db:
            await db.execute(
                """INSERT OR REPLACE INTO player_profiles
                   (player_id, blizzard_id, html_compressed, summary_json, last_updated_blizzard,
                    created_at, updated_at, schema_version)
                   VALUES (?, ?, ?, ?, ?,
                           COALESCE((SELECT created_at FROM player_profiles WHERE player_id = ?), ?),
                           ?, ?)""",
                (
                    player_id,
                    blizzard_id,
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

    async def get_player_status(self, player_id: str) -> dict | None:
        """
        Get player status for unknown player tracking.

        Returns:
            Dict with 'check_count', 'last_checked_at', 'retry_after' or None if not found
        """
        async with (
            self._get_connection() as db,
            db.execute(
                """SELECT check_count, last_checked_at, retry_after
                   FROM player_status WHERE player_id = ?""",
                (player_id,),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            if not row:
                return None

            return {
                "check_count": row[0],
                "last_checked_at": row[1],
                "retry_after": row[2],
            }

    async def set_player_status(
        self, player_id: str, check_count: int, retry_after: int
    ) -> None:
        """
        Set player status for unknown player tracking with exponential backoff.

        Args:
            player_id: Player identifier
            check_count: Number of times we've checked and not found this player
            retry_after: Seconds until next recheck is allowed
        """
        now = int(time.time())

        async with self._get_connection() as db:
            await db.execute(
                """INSERT OR REPLACE INTO player_status
                   (player_id, check_count, last_checked_at, retry_after)
                   VALUES (?, ?, ?, ?)""",
                (player_id, check_count, now, retry_after),
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
        Get storage statistics for Prometheus metrics.

        Returns:
            Dict with counts per table and total database size
        """
        async with self._get_connection() as db:
            # Count entries per table
            async with db.execute("SELECT COUNT(*) FROM static_data") as cursor:
                row = await cursor.fetchone()
                static_count = row[0] if row else 0

            async with db.execute("SELECT COUNT(*) FROM player_profiles") as cursor:
                row = await cursor.fetchone()
                profiles_count = row[0] if row else 0

            async with db.execute("SELECT COUNT(*) FROM player_status") as cursor:
                row = await cursor.fetchone()
                status_count = row[0] if row else 0

        # Get file size (or estimate for in-memory database)
        if self.db_path == MEMORY_DB:
            # Estimate size for in-memory database
            # Rough approximation: static_data ~1KB, player_profiles ~10KB, player_status ~100B
            size_bytes = (
                (static_count * 1024) + (profiles_count * 10240) + (status_count * 100)
            )
        else:
            db_file = Path(self.db_path)
            size_bytes = db_file.stat().st_size if db_file.exists() else 0

        return {
            "size_bytes": size_bytes,
            "static_data_count": static_count,
            "player_profiles_count": profiles_count,
            "player_status_count": status_count,
        }

    async def clear_all_data(self) -> None:
        """Clear all data including static data (for testing)"""
        async with self._get_connection() as db:
            await db.execute("DELETE FROM static_data")
            await db.execute("DELETE FROM player_profiles")
            await db.execute("DELETE FROM player_status")
            await db.commit()
