"""Valkey-backed background worker.

Runs a BRPOP loop that pops jobs from a Valkey List and executes them
concurrently as asyncio tasks.  A lightweight cron check fires
``check_new_hero`` once daily at 02:00 UTC using a Valkey NX key to prevent
duplicate runs after worker restarts.

Run with::

    python -m app.adapters.tasks.valkey_worker
"""

import asyncio
import json
import signal
import time
from datetime import UTC, datetime
from typing import Any

import valkey.asyncio as valkey_async

from app.adapters.blizzard import OverFastClient
from app.adapters.blizzard.parsers.heroes import fetch_heroes_html, parse_heroes_html
from app.adapters.cache import CacheManager
from app.adapters.storage import PostgresStorage
from app.adapters.tasks.valkey_task_queue import JOB_KEY_PREFIX, JOB_TTL, QUEUE_KEY
from app.config import settings
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

_CRON_KEY_PREFIX = "worker:cron:check_new_hero:"


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


async def startup() -> dict[str, Any]:
    """Initialize shared adapters once per worker process."""
    logger.info("[Worker] Starting up...")
    storage = PostgresStorage()
    await storage.initialize()
    cache = CacheManager()
    blizzard_client = OverFastClient()
    from app.adapters.tasks.valkey_task_queue import ValkeyTaskQueue  # noqa: PLC0415

    task_queue = ValkeyTaskQueue()
    # Dedicated Valkey client for BRPOP (avoids blocking the shared ValkeyCache pool)
    valkey_client = valkey_async.Valkey(
        host=settings.valkey_host, port=settings.valkey_port, protocol=3
    )
    logger.info("[Worker] Ready.")
    return {
        "storage": storage,
        "cache": cache,
        "blizzard_client": blizzard_client,
        "task_queue": task_queue,
        "valkey": valkey_client,
    }


async def shutdown(ctx: dict[str, Any]) -> None:
    """Clean up adapters on worker shutdown."""
    logger.info("[Worker] Shutting down...")
    if blizzard_client := ctx.get("blizzard_client"):
        await blizzard_client.aclose()
    if storage := ctx.get("storage"):
        await storage.close()
    if valkey_client := ctx.get("valkey"):
        await valkey_client.aclose()
    logger.info("[Worker] Stopped.")


# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------


def _make_hero_service(ctx: dict[str, Any]) -> HeroService:
    return HeroService(ctx["cache"], ctx["storage"], ctx["blizzard_client"], ctx["task_queue"])


def _make_role_service(ctx: dict[str, Any]) -> RoleService:
    return RoleService(ctx["cache"], ctx["storage"], ctx["blizzard_client"], ctx["task_queue"])


def _make_map_service(ctx: dict[str, Any]) -> MapService:
    return MapService(ctx["cache"], ctx["storage"], ctx["blizzard_client"], ctx["task_queue"])


def _make_gamemode_service(ctx: dict[str, Any]) -> GamemodeService:
    return GamemodeService(ctx["cache"], ctx["storage"], ctx["blizzard_client"], ctx["task_queue"])


def _make_player_service(ctx: dict[str, Any]) -> PlayerService:
    return PlayerService(ctx["cache"], ctx["storage"], ctx["blizzard_client"], ctx["task_queue"])


# ---------------------------------------------------------------------------
# Task handlers — parse entity_id (storage key) and call the right service
# ---------------------------------------------------------------------------


async def _run_refresh_heroes(ctx: dict[str, Any], entity_id: str) -> None:
    """entity_id format: ``heroes:{locale}``  e.g. ``heroes:en-us``"""
    _, locale_str = entity_id.split(":", 1)
    locale = Locale(locale_str)
    cache_key = f"/heroes?locale={locale_str}" if locale != Locale.ENGLISH_US else "/heroes"
    await _make_hero_service(ctx).list_heroes(
        locale=locale, role=None, gamemode=None, cache_key=cache_key
    )


async def _run_refresh_hero(ctx: dict[str, Any], entity_id: str) -> None:
    """entity_id format: ``hero:{hero_key}:{locale}``  e.g. ``hero:ana:en-us``"""
    _, hero_key, locale_str = entity_id.split(":", 2)
    locale = Locale(locale_str)
    cache_key = (
        f"/heroes/{hero_key}?locale={locale_str}"
        if locale != Locale.ENGLISH_US
        else f"/heroes/{hero_key}"
    )
    await _make_hero_service(ctx).get_hero(
        hero_key=hero_key, locale=locale, cache_key=cache_key
    )


async def _run_refresh_roles(ctx: dict[str, Any], entity_id: str) -> None:
    """entity_id format: ``roles:{locale}``  e.g. ``roles:en-us``"""
    _, locale_str = entity_id.split(":", 1)
    locale = Locale(locale_str)
    cache_key = f"/roles?locale={locale_str}" if locale != Locale.ENGLISH_US else "/roles"
    await _make_role_service(ctx).list_roles(locale=locale, cache_key=cache_key)


async def _run_refresh_maps(ctx: dict[str, Any], entity_id: str) -> None:  # noqa: ARG001
    """entity_id format: ``maps:all``"""
    await _make_map_service(ctx).list_maps(gamemode=None, cache_key="/maps")


async def _run_refresh_gamemodes(ctx: dict[str, Any], entity_id: str) -> None:  # noqa: ARG001
    """entity_id format: ``gamemodes:all``"""
    await _make_gamemode_service(ctx).list_gamemodes(cache_key="/gamemodes")


async def _run_refresh_player_profile(ctx: dict[str, Any], entity_id: str) -> None:
    """entity_id is the player_id string."""
    await _make_player_service(ctx).get_player_career(
        entity_id, gamemode=None, platform=None, cache_key=f"/players/{entity_id}"
    )


_TASK_HANDLERS: dict[str, Any] = {
    "refresh_heroes": _run_refresh_heroes,
    "refresh_hero": _run_refresh_hero,
    "refresh_roles": _run_refresh_roles,
    "refresh_maps": _run_refresh_maps,
    "refresh_gamemodes": _run_refresh_gamemodes,
    "refresh_player_profile": _run_refresh_player_profile,
}


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------


async def _execute_job(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Execute a single job, update job state in Valkey, and clean up."""
    task_name: str = payload["task"]
    job_id: str = payload["job_id"]
    args: list = payload.get("args", [])
    entity_id: str = args[0] if args else ""

    handler = _TASK_HANDLERS.get(task_name)
    if handler is None:
        logger.warning(f"[Worker] Unknown task: {task_name!r} — skipping")
        return

    valkey_client: valkey_async.Valkey = ctx["valkey"]
    await valkey_client.set(f"{JOB_KEY_PREFIX}{job_id}", "running", ex=JOB_TTL)

    start = time.monotonic()
    try:
        logger.info(f"[Worker] Running {task_name} (job_id={job_id})")
        await handler(ctx, entity_id)
        elapsed = time.monotonic() - start
        logger.info(f"[Worker] Completed {task_name} in {elapsed:.2f}s (job_id={job_id})")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Worker] Task {task_name} failed (job_id={job_id}): {exc}")
    finally:
        await valkey_client.delete(f"{JOB_KEY_PREFIX}{job_id}")


# ---------------------------------------------------------------------------
# Cron: check_new_hero at 02:00 UTC daily
# ---------------------------------------------------------------------------


async def check_new_hero(ctx: dict[str, Any]) -> None:
    """Compare Blizzard hero list to local HeroKey enum; notify Discord on new heroes."""
    if not settings.discord_webhook_enabled:
        logger.debug("[Worker] check_new_hero: Discord webhook disabled, skipping.")
        return

    logger.info("[Worker] check_new_hero: Checking for new heroes...")
    try:
        html = await fetch_heroes_html(ctx["blizzard_client"])
        heroes = parse_heroes_html(html)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Worker] check_new_hero: Failed to fetch heroes: {exc}")
        return

    new_keys = {hero["key"] for hero in heroes} - set(HeroKey)
    if new_keys:
        logger.info(f"[Worker] check_new_hero: New heroes found: {new_keys}")
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
    else:
        logger.info("[Worker] check_new_hero: No new heroes found.")


async def _maybe_run_cron(ctx: dict[str, Any]) -> None:
    """Fire check_new_hero at 02:00 UTC, at most once per calendar day."""
    now = datetime.now(UTC)
    if now.hour != 2:  # noqa: PLR2004
        return
    today = now.date().isoformat()
    valkey_client: valkey_async.Valkey = ctx["valkey"]
    claimed = await valkey_client.set(
        f"{_CRON_KEY_PREFIX}{today}", "1", nx=True, ex=86400
    )
    if claimed:
        logger.info("[Worker] Cron: triggering check_new_hero")
        await check_new_hero(ctx)


# ---------------------------------------------------------------------------
# Main worker loop
# ---------------------------------------------------------------------------


async def _worker_loop(ctx: dict[str, Any], stop_event: asyncio.Event) -> None:
    """Pop jobs from the Valkey queue and execute them as concurrent asyncio tasks."""
    valkey_client: valkey_async.Valkey = ctx["valkey"]
    max_jobs: int = settings.worker_max_concurrent_jobs
    running_tasks: set[asyncio.Task] = set()

    logger.info(f"[Worker] Listening on '{QUEUE_KEY}' (max_concurrent={max_jobs})...")

    while not stop_event.is_set():
        # Enforce concurrency limit before blocking on BRPOP
        running_tasks = {t for t in running_tasks if not t.done()}
        if len(running_tasks) >= max_jobs:
            await asyncio.sleep(0.1)
            continue

        try:
            result = await valkey_client.brpop(QUEUE_KEY, timeout=1)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Worker] BRPOP error: {exc}")
            await asyncio.sleep(1)
            continue

        if result is not None:
            _, payload_bytes = result
            try:
                payload = json.loads(payload_bytes)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"[Worker] Invalid job payload: {payload_bytes!r}")
                continue
            task = asyncio.create_task(
                _execute_job(ctx, payload), name=payload.get("job_id", "unknown")
            )
            running_tasks.add(task)

        await _maybe_run_cron(ctx)

    # Drain in-flight tasks before exiting
    if running_tasks:
        logger.info(f"[Worker] Waiting for {len(running_tasks)} in-flight task(s)...")
        await asyncio.gather(*running_tasks, return_exceptions=True)


async def main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    ctx = await startup()
    try:
        await _worker_loop(ctx, stop_event)
    finally:
        await shutdown(ctx)


if __name__ == "__main__":
    asyncio.run(main())
