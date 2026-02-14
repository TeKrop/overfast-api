"""Monitoring router for Prometheus metrics endpoint"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.adapters.storage import SQLiteStorage
from app.monitoring.metrics import storage_entries_total, storage_size_bytes
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
    """
    # Collect SQLite storage metrics (Phase 3)
    try:
        storage: StoragePort = SQLiteStorage()
        stats = await storage.get_stats()

        # Update Prometheus gauges
        storage_size_bytes.set(stats["size_bytes"])
        storage_entries_total.labels(table="static_data").set(
            stats["static_data_count"],
        )
        storage_entries_total.labels(table="player_profiles").set(
            stats["player_profiles_count"],
        )
        storage_entries_total.labels(table="player_status").set(
            stats["player_status_count"],
        )
    except Exception as err:  # noqa: BLE001
        # Don't fail metrics endpoint if storage stats unavailable
        logger.warning(f"Failed to collect storage metrics: {err}")

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
