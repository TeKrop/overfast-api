"""Monitoring router for Prometheus metrics endpoint"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.adapters.storage import SQLiteStorage
from app.monitoring.metrics import (
    sqlite_player_profile_age_seconds,
    sqlite_wal_size_bytes,
    storage_entries_total,
    storage_size_bytes,
)
from app.overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import StoragePort

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Collects current SQLite storage statistics before generating metrics.
    All other metrics (API requests, Blizzard calls, etc.) are updated
    in real-time via middleware and adapters.

    Phase 3.5B: Enhanced with comprehensive SQLite metrics including
    data freshness, WAL size, etc.
    """
    # Collect SQLite storage metrics
    try:
        storage: StoragePort = SQLiteStorage()
        stats = await storage.get_stats()

        # Core storage metrics
        storage_size_bytes.set(stats["size_bytes"])
        storage_entries_total.labels(table="static_data").set(
            stats["static_data_count"],
        )
        storage_entries_total.labels(table="player_profiles").set(
            stats["player_profiles_count"],
        )

        # Phase 3.5B: Enhanced metrics
        sqlite_wal_size_bytes.set(stats.get("wal_size_bytes", 0))

        # Data freshness (player profile ages)
        # Set gauges rather than observe to show current state
        if stats.get("player_profile_age_p50", 0) > 0:
            # Use histogram to track distribution
            sqlite_player_profile_age_seconds.observe(
                stats.get("player_profile_age_p50", 0)
            )
            sqlite_player_profile_age_seconds.observe(
                stats.get("player_profile_age_p90", 0)
            )
            sqlite_player_profile_age_seconds.observe(
                stats.get("player_profile_age_p99", 0)
            )

    except Exception as err:  # noqa: BLE001
        # Don't fail metrics endpoint if storage stats unavailable
        logger.warning(f"Failed to collect storage metrics: {err}")

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
