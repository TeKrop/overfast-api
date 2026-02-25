"""Monitoring router for Prometheus metrics endpoint"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.adapters.storage import PostgresStorage
from app.monitoring.metrics import (
    storage_entries_total,
    storage_player_profile_age_seconds,
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

    Collects current storage statistics before generating metrics.
    All other metrics (API requests, Blizzard calls, etc.) are updated
    in real-time via middleware and adapters.
    """
    # Collect storage metrics
    try:
        storage: StoragePort = PostgresStorage()
        stats = await storage.get_stats()

        # Core storage metrics
        storage_size_bytes.set(stats["size_bytes"])
        storage_entries_total.labels(table="static_data").set(
            stats["static_data_count"],
        )
        storage_entries_total.labels(table="player_profiles").set(
            stats["player_profiles_count"],
        )

        # Data freshness (player profile ages)
        if stats.get("player_profile_age_p50", 0) > 0:
            storage_player_profile_age_seconds.observe(
                stats.get("player_profile_age_p50", 0)
            )
            storage_player_profile_age_seconds.observe(
                stats.get("player_profile_age_p90", 0)
            )
            storage_player_profile_age_seconds.observe(
                stats.get("player_profile_age_p99", 0)
            )

    except Exception as err:  # noqa: BLE001
        # Don't fail metrics endpoint if storage stats unavailable
        logger.warning(f"Failed to collect storage metrics: {err}")

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
