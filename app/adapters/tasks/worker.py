"""Background worker tasks for OverFast API.

Tasks are executed by the taskiq worker process::

    taskiq worker app.adapters.tasks.worker:broker

The cron task ``check_new_hero`` is scheduled by the taskiq scheduler::

    taskiq scheduler app.adapters.tasks.worker:scheduler

:func:`taskiq_fastapi.init` wires FastAPI's dependency injection so each task
function receives its service dependencies from the same DI container used by
the API server (including any overrides set in ``app.main``).
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated

from prometheus_client import start_http_server

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from taskiq import TaskiqDepends, TaskiqEvents
from taskiq.schedule_sources import LabelScheduleSource
from taskiq.scheduler.scheduler import TaskiqScheduler
from taskiq_fastapi import init as taskiq_init

from app.adapters.tasks.task_registry import TASK_MAP
from app.adapters.tasks.valkey_broker import ValkeyListBroker
from app.api.dependencies import (
    get_blizzard_client,
    get_gamemode_service,
    get_hero_service,
    get_map_service,
    get_player_service,
    get_role_service,
    get_storage,
    get_task_queue,
)
from app.api.helpers import send_discord_webhook_message
from app.config import settings
from app.domain.enums import HeroKey, Locale
from app.domain.parsers.heroes import fetch_heroes_html, parse_heroes_html
from app.domain.ports import BlizzardClientPort, StoragePort, TaskQueuePort
from app.domain.services import (
    GamemodeService,
    HeroService,
    MapService,
    PlayerService,
    RoleService,
)
from app.infrastructure.logger import logger
from app.monitoring.metrics import (
    background_refresh_completed_total,
    background_refresh_failed_total,
    background_tasks_duration_seconds,
)

# ─── Broker ───────────────────────────────────────────────────────────────────

broker = ValkeyListBroker(
    url=f"valkey://{settings.valkey_host}:{settings.valkey_port}",
    queue_name="taskiq:queue",
)

# Wire FastAPI DI into taskiq tasks.
# In worker mode this also triggers the FastAPI lifespan (DB init, cache eviction…).
taskiq_init(broker, "app.main:app")


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def start_metrics_server(state: object) -> None:  # noqa: ARG001
    """Expose a Prometheus /metrics endpoint from the worker process."""
    if settings.prometheus_enabled:
        start_http_server(settings.prometheus_worker_port)
        logger.info(
            "[Worker] Prometheus metrics server started on port {}",
            settings.prometheus_worker_port,
        )


# ─── Scheduler (cron) ────────────────────────────────────────────────────────

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

# ─── Dependency type aliases ─────────────────────────────────────────────────

HeroServiceDep = Annotated[HeroService, TaskiqDepends(get_hero_service)]
RoleServiceDep = Annotated[RoleService, TaskiqDepends(get_role_service)]
MapServiceDep = Annotated[MapService, TaskiqDepends(get_map_service)]
GamemodeServiceDep = Annotated[GamemodeService, TaskiqDepends(get_gamemode_service)]
PlayerServiceDep = Annotated[PlayerService, TaskiqDepends(get_player_service)]
BlizzardClientDep = Annotated[BlizzardClientPort, TaskiqDepends(get_blizzard_client)]
StorageDep = Annotated[StoragePort, TaskiqDepends(get_storage)]
TaskQueueDep = Annotated[TaskQueuePort, TaskiqDepends(get_task_queue)]


# ─── Metrics helper ──────────────────────────────────────────────────────────


@asynccontextmanager
async def _run_refresh_task(
    entity_type: str,
    entity_id: str,
    task_queue: TaskQueuePort,
) -> AsyncIterator[None]:
    """Context manager that executes a refresh task end-to-end: records
    duration and success/failure metrics, then releases the dedup key so
    the job can be re-enqueued immediately after completion.
    """
    start = time.monotonic()
    duration = 0.0
    try:
        yield
        duration = time.monotonic() - start
        background_refresh_completed_total.labels(entity_type=entity_type).inc()
        logger.info("[Worker] Refresh completed: {} in {:.3f}s", entity_id, duration)
    except Exception as exc:
        duration = time.monotonic() - start
        background_refresh_failed_total.labels(entity_type=entity_type).inc()
        logger.warning(
            "[Worker] Refresh failed: {} — {} ({:.3f}s)", entity_id, exc, duration
        )
        raise
    finally:
        background_tasks_duration_seconds.labels(entity_type=entity_type).observe(
            duration
        )
        await task_queue.release_job(entity_id)


# ─── Refresh tasks ────────────────────────────────────────────────────────────


@broker.task
async def refresh_heroes(
    entity_id: str, service: HeroServiceDep, task_queue: TaskQueueDep
) -> None:
    """Refresh the heroes list for one locale.

    ``entity_id`` format: ``heroes:{locale}``  e.g. ``heroes:en-us``
    """
    _, locale_str = entity_id.split(":", 1)
    async with _run_refresh_task("heroes", entity_id, task_queue):
        await service.refresh_list(Locale(locale_str))


@broker.task
async def refresh_hero(
    entity_id: str, service: HeroServiceDep, task_queue: TaskQueueDep
) -> None:
    """Refresh a single hero for one locale.

    ``entity_id`` format: ``hero:{hero_key}:{locale}``  e.g. ``hero:ana:en-us``
    """
    _, hero_key, locale_str = entity_id.split(":", 2)
    async with _run_refresh_task("hero", entity_id, task_queue):
        await service.refresh_single(hero_key, Locale(locale_str))


@broker.task
async def refresh_roles(
    entity_id: str, service: RoleServiceDep, task_queue: TaskQueueDep
) -> None:
    """Refresh roles for one locale.

    ``entity_id`` format: ``roles:{locale}``  e.g. ``roles:en-us``
    """
    _, locale_str = entity_id.split(":", 1)
    async with _run_refresh_task("roles", entity_id, task_queue):
        await service.refresh_list(Locale(locale_str))


@broker.task
async def refresh_maps(
    entity_id: str,
    service: MapServiceDep,
    task_queue: TaskQueueDep,
) -> None:
    """Refresh all maps. ``entity_id`` is always ``maps:all``."""
    async with _run_refresh_task("maps", entity_id, task_queue):
        await service.refresh_list()


@broker.task
async def refresh_gamemodes(
    entity_id: str,
    service: GamemodeServiceDep,
    task_queue: TaskQueueDep,
) -> None:
    """Refresh all game modes. ``entity_id`` is always ``gamemodes:all``."""
    async with _run_refresh_task("gamemodes", entity_id, task_queue):
        await service.refresh_list()


@broker.task
async def refresh_player_profile(
    entity_id: str, service: PlayerServiceDep, task_queue: TaskQueueDep
) -> None:
    """Refresh a player career profile.

    ``entity_id`` is the raw ``player_id`` string.
    Calls :meth:`~app.domain.services.PlayerService.refresh_player_profile`
    which bypasses the persistent-storage fast-path to guarantee a live
    Blizzard fetch regardless of how recently the profile was stored.
    """
    async with _run_refresh_task("player", entity_id, task_queue):
        await service.refresh_player_profile(entity_id)


# ─── Cron tasks ───────────────────────────────────────────────────────────────


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def cleanup_stale_players(storage: StorageDep) -> None:
    """Delete player profiles older than ``player_profile_max_age`` (runs daily at 03:00 UTC)."""
    if settings.player_profile_max_age <= 0:
        logger.debug(
            "[Worker] cleanup_stale_players: disabled (max_age <= 0), skipping."
        )
        return

    logger.info("[Worker] cleanup_stale_players: Deleting stale player profiles...")
    try:
        await storage.delete_old_player_profiles(settings.player_profile_max_age)
    except Exception:  # noqa: BLE001
        logger.exception("[Worker] cleanup_stale_players: Failed.")
        return

    logger.info("[Worker] cleanup_stale_players: Done.")


@broker.task(schedule=[{"cron": "0 2 * * *"}])
async def check_new_hero(client: BlizzardClientDep) -> None:
    """Detect new Blizzard heroes and notify via Discord (runs daily at 02:00 UTC)."""
    if not settings.discord_webhook_enabled:
        logger.debug("[Worker] check_new_hero: Discord webhook disabled, skipping.")
        return

    logger.info("[Worker] check_new_hero: Checking for new heroes...")
    try:
        html = await fetch_heroes_html(client)
        heroes = parse_heroes_html(html)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Worker] check_new_hero: Failed to fetch heroes: {}", exc)
        return

    new_keys = {hero["key"] for hero in heroes} - set(HeroKey)
    if not new_keys:
        logger.info("[Worker] check_new_hero: No new heroes found.")
        return

    logger.info("[Worker] check_new_hero: New heroes found: {}", new_keys)
    send_discord_webhook_message(
        title="🎮 New Heroes Detected",
        description="New Overwatch heroes have been released!",
        fields=[
            {
                "name": "Hero Keys",
                "value": f"`{', '.join(sorted(new_keys))}`",
                "inline": False,
            },
            {
                "name": "Action Required",
                "value": "Please add these keys to the `HeroKey` enum configuration.",
                "inline": False,
            },
        ],
        color=0x2ECC71,
    )


# ─── Task registry (used by ValkeyTaskQueue for dispatch) ────────────────────

TASK_MAP.update(
    {
        "refresh_heroes": refresh_heroes,
        "refresh_hero": refresh_hero,
        "refresh_roles": refresh_roles,
        "refresh_maps": refresh_maps,
        "refresh_gamemodes": refresh_gamemodes,
        "refresh_player_profile": refresh_player_profile,
    }
)
