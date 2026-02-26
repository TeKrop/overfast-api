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

from typing import Annotated

from taskiq import TaskiqDepends
from taskiq.schedule_sources import LabelScheduleSource
from taskiq.scheduler.scheduler import TaskiqScheduler
from taskiq_fastapi import init as taskiq_init

from app.adapters.blizzard.parsers.heroes import fetch_heroes_html, parse_heroes_html
from app.adapters.tasks.valkey_broker import ValkeyListBroker
from app.api.dependencies import (
    get_blizzard_client,
    get_gamemode_service,
    get_hero_service,
    get_map_service,
    get_player_service,
    get_role_service,
)
from app.config import settings
from app.domain.ports import BlizzardClientPort
from app.domain.services import (
    GamemodeService,
    HeroService,
    MapService,
    PlayerService,
    RoleService,
)
from app.enums import Locale
from app.helpers import send_discord_webhook_message
from app.heroes.enums import HeroKey
from app.overfast_logger import logger

# ─── Broker ───────────────────────────────────────────────────────────────────

broker = ValkeyListBroker(
    url=f"valkey://{settings.valkey_host}:{settings.valkey_port}",
    queue_name="taskiq:queue",
)

# Wire FastAPI DI into taskiq tasks.
# In worker mode this also triggers the FastAPI lifespan (DB init, cache eviction…).
taskiq_init(broker, "app.main:app")

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


# ─── Refresh tasks ────────────────────────────────────────────────────────────


@broker.task
async def refresh_heroes(entity_id: str, service: HeroServiceDep) -> None:
    """Refresh the heroes list for one locale.

    ``entity_id`` format: ``heroes:{locale}``  e.g. ``heroes:en-us``
    """
    _, locale_str = entity_id.split(":", 1)
    locale = Locale(locale_str)
    cache_key = f"/heroes?locale={locale_str}" if locale != Locale.ENGLISH_US else "/heroes"
    await service.list_heroes(locale=locale, role=None, gamemode=None, cache_key=cache_key)


@broker.task
async def refresh_hero(entity_id: str, service: HeroServiceDep) -> None:
    """Refresh a single hero for one locale.

    ``entity_id`` format: ``hero:{hero_key}:{locale}``  e.g. ``hero:ana:en-us``
    """
    _, hero_key, locale_str = entity_id.split(":", 2)
    locale = Locale(locale_str)
    cache_key = (
        f"/heroes/{hero_key}?locale={locale_str}"
        if locale != Locale.ENGLISH_US
        else f"/heroes/{hero_key}"
    )
    await service.get_hero(hero_key=hero_key, locale=locale, cache_key=cache_key)


@broker.task
async def refresh_roles(entity_id: str, service: RoleServiceDep) -> None:
    """Refresh roles for one locale.

    ``entity_id`` format: ``roles:{locale}``  e.g. ``roles:en-us``
    """
    _, locale_str = entity_id.split(":", 1)
    locale = Locale(locale_str)
    cache_key = f"/roles?locale={locale_str}" if locale != Locale.ENGLISH_US else "/roles"
    await service.list_roles(locale=locale, cache_key=cache_key)


@broker.task
async def refresh_maps(entity_id: str, service: MapServiceDep) -> None:  # noqa: ARG001
    """Refresh all maps. ``entity_id`` is always ``maps:all``."""
    await service.list_maps(gamemode=None, cache_key="/maps")


@broker.task
async def refresh_gamemodes(entity_id: str, service: GamemodeServiceDep) -> None:  # noqa: ARG001
    """Refresh all game modes. ``entity_id`` is always ``gamemodes:all``."""
    await service.list_gamemodes(cache_key="/gamemodes")


@broker.task
async def refresh_player_profile(entity_id: str, service: PlayerServiceDep) -> None:
    """Refresh a player career profile.

    ``entity_id`` is the raw ``player_id`` string.
    """
    await service.get_player_career(
        entity_id, gamemode=None, platform=None, cache_key=f"/players/{entity_id}"
    )


# ─── Cron task ────────────────────────────────────────────────────────────────


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
        logger.warning("[Worker] check_new_hero: Failed to fetch heroes: %s", exc)
        return

    new_keys = {hero["key"] for hero in heroes} - set(HeroKey)
    if not new_keys:
        logger.info("[Worker] check_new_hero: No new heroes found.")
        return

    logger.info("[Worker] check_new_hero: New heroes found: %s", new_keys)
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

TASK_MAP = {
    "refresh_heroes": refresh_heroes,
    "refresh_hero": refresh_hero,
    "refresh_roles": refresh_roles,
    "refresh_maps": refresh_maps,
    "refresh_gamemodes": refresh_gamemodes,
    "refresh_player_profile": refresh_player_profile,
}
