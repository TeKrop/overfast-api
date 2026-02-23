"""In-memory FakeStorage implementing StoragePort — used in tests only."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.ports.storage import StaticDataCategory


class FakeStorage:
    """
    In-memory storage stub that satisfies ``StoragePort``.

    All data lives in plain dicts — no DB, no compression, no I/O.
    Provides the same interface as ``PostgresStorage`` so unit tests
    run without a real database.
    """

    def __init__(self) -> None:
        self._static: dict[str, dict] = {}
        self._profiles: dict[str, dict] = {}
        self._battletag_index: dict[str, str] = {}

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    # ------------------------------------------------------------------ #
    # Static data
    # ------------------------------------------------------------------ #

    async def get_static_data(self, key: str) -> dict | None:
        return self._static.get(key)

    async def set_static_data(
        self,
        key: str,
        data: dict,
        category: StaticDataCategory,
        data_version: int = 1,
    ) -> None:
        now = int(time.time())
        existing = self._static.get(key)
        self._static[key] = {
            "data": data,
            "category": str(category),
            "data_version": data_version,
            "updated_at": now,
            "created_at": existing["created_at"] if existing else now,
        }

    # ------------------------------------------------------------------ #
    # Player profiles
    # ------------------------------------------------------------------ #

    async def get_player_profile(self, player_id: str) -> dict | None:
        profile = self._profiles.get(player_id)
        if profile is None:
            return None
        summary = profile.get("summary") or {}
        if not summary:
            summary = {"url": player_id, "lastUpdated": profile.get("last_updated_blizzard")}
        return {**profile, "summary": summary}

    async def get_player_id_by_battletag(self, battletag: str) -> str | None:
        return self._battletag_index.get(battletag)

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
        now = int(time.time())
        existing = self._profiles.get(player_id)
        self._profiles[player_id] = {
            "html": html,
            "summary": summary or {},
            "battletag": battletag or (existing["battletag"] if existing else None),
            "name": name or (existing["name"] if existing else None),
            "last_updated_blizzard": last_updated_blizzard,
            "updated_at": now,
            "created_at": existing["created_at"] if existing else now,
            "data_version": data_version,
        }
        if battletag:
            self._battletag_index[battletag] = player_id

    # ------------------------------------------------------------------ #
    # Maintenance
    # ------------------------------------------------------------------ #

    async def delete_old_player_profiles(self, max_age_seconds: int) -> int:
        cutoff = time.time() - max_age_seconds
        to_delete = [
            pid
            for pid, p in self._profiles.items()
            if p["updated_at"] < cutoff
        ]
        for pid in to_delete:
            bt = self._profiles[pid].get("battletag")
            if bt:
                self._battletag_index.pop(bt, None)
            del self._profiles[pid]
        return len(to_delete)

    async def clear_all_data(self) -> None:
        self._static.clear()
        self._profiles.clear()
        self._battletag_index.clear()

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #

    async def get_stats(self) -> dict:
        now = time.time()
        ages = sorted(now - p["updated_at"] for p in self._profiles.values())
        n = len(ages)
        return {
            "size_bytes": 0,
            "static_data_count": len(self._static),
            "player_profiles_count": n,
            "player_profile_age_p50": ages[n // 2] if ages else 0,
            "player_profile_age_p90": ages[int(n * 0.9)] if ages else 0,
            "player_profile_age_p99": ages[int(n * 0.99)] if ages else 0,
        }
