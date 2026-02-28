"""Project main file containing FastAPI app and routes definitions"""

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .adapters.blizzard import OverFastClient
from .adapters.cache import CacheManager
from .adapters.storage import PostgresStorage
from .adapters.tasks.worker import broker
from .api.enums import Profiler, RouteTag
from .api.routers.gamemodes import router as gamemodes
from .api.routers.heroes import router as heroes
from .api.routers.maps import router as maps
from .api.routers.players import router as players
from .api.routers.roles import router as roles
from .config import settings
from .docs import render_documentation
from .helpers import overfast_internal_error
from .middlewares import (
    MemrayInMemoryMiddleware,
    ObjGraphMiddleware,
    PyInstrumentMiddleware,
    TraceMallocMiddleware,
)
from .monitoring.middleware import register_prometheus_middleware
from .overfast_logger import logger

if TYPE_CHECKING:
    from app.domain.ports import BlizzardClientPort, CachePort, StoragePort


if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        # Enable sending logs to Sentry
        enable_logs=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profile_session_sample_rate to 1.0 to profile 100%
        # of profile sessions.
        profile_session_sample_rate=1.0,
        # Set profile_lifecycle to "trace" to automatically
        # run the profiler on when there is an active transaction
        profile_lifecycle="trace",
        # Set a human-readable release identifier.
        release=settings.app_version,
    )


_CLEANUP_INTERVAL = 86400  # seconds between each player profile cleanup run


async def _player_profile_cleanup_loop(
    storage: StoragePort, max_age_seconds: int
) -> None:
    """Background task: delete stale player profiles every hour."""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL)
        try:
            await storage.delete_old_player_profiles(max_age_seconds)
        except asyncio.CancelledError:
            # Let task cancellation propagate so shutdown behaves correctly.
            raise
        except Exception:  # noqa: BLE001
            # Log unexpected errors but keep the cleanup loop running.
            logger.exception("Player profile cleanup task failed")


@asynccontextmanager
async def lifespan(_: FastAPI):  # pragma: no cover
    logger.info("Initializing PostgreSQL storage...")
    storage: StoragePort = PostgresStorage()
    await storage.initialize()

    logger.info("Instanciating HTTPX AsyncClient...")
    overfast_client: BlizzardClientPort = OverFastClient()

    # Evict stale api-cache data on startup (handles crash/deploy scenarios)
    cache: CachePort = CacheManager()
    await cache.evict_volatile_data()

    # Start broker for task dispatch (skipped in worker mode — taskiq handles it).
    if not broker.is_worker_process:
        logger.info("Starting Valkey task broker...")
        await broker.startup()

    cleanup_task: asyncio.Task | None = None
    if settings.player_profile_max_age > 0:
        cleanup_task = asyncio.create_task(
            _player_profile_cleanup_loop(storage, settings.player_profile_max_age)
        )

    yield

    if cleanup_task is not None:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

    # Properly close HTTPX Async Client and PostgreSQL storage
    await overfast_client.aclose()

    # Evict volatile Valkey data (api-cache, rate-limit, etc.) before RDB snapshot
    await cache.evict_volatile_data()
    await cache.bgsave()

    await storage.close()

    if not broker.is_worker_process:
        await broker.shutdown()


description = f"""OverFast API provides comprehensive data on Overwatch heroes,
game modes, maps, and player statistics by scraping Blizzard pages. Developed with
the efficiency of **FastAPI** and **Selectolax**, it leverages **nginx (OpenResty)** as a
reverse proxy and **Valkey** for caching. Its tailored caching mechanism significantly
reduces calls to Blizzard pages, ensuring swift and precise data delivery to users.

This live instance is configured with the following restrictions:
- Rate Limit per IP: **{settings.rate_limit_per_second_per_ip} requests/second** (burst capacity :
**{settings.rate_limit_per_ip_burst}**)
- Maximum connections/simultaneous requests per IP: **{settings.max_connections_per_ip}**
- Adaptive Blizzard throttle: **{settings.throttle_start_delay}s** initial delay
  (auto-adjusts based on Blizzard response latency; 503 returned when rate-limited)

This limit may be adjusted as needed. If you require higher throughput, consider
hosting your own instance on a server 👍

Swagger UI (useful for trying API calls) : {settings.app_base_url}/docs

{f"Status page : {settings.status_page_url}" if settings.status_page_url else ""}
"""

players_section_description = """Overwatch players data : summary, statistics, etc.

In player career statistics, various conversions are applied for ease of use:
- **Duration values** are converted to **seconds** (integer)
- **Percent values** are represented as **integers**, omitting the percent symbol
- Integer and float string representations are converted to their respective types
"""


# Custom JSONResponse class that enforces ASCII encoding
class ASCIIJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(
    title="OverFast API",
    description=description,
    version=settings.app_version,
    openapi_tags=[
        {
            "name": RouteTag.HEROES,
            "description": "Overwatch heroes details : lore, abilities, etc.",
            "externalDocs": {
                "description": "Blizzard heroes page, source of the information",
                "url": "https://overwatch.blizzard.com/en-us/heroes/",
            },
        },
        {
            "name": RouteTag.GAMEMODES,
            "description": "Overwatch gamemodes details",
            "externalDocs": {
                "description": "Overwatch home page, source of the information",
                "url": "https://overwatch.blizzard.com/en-us/",
            },
        },
        {
            "name": RouteTag.MAPS,
            "description": "Overwatch maps details",
        },
        {
            "name": RouteTag.PLAYERS,
            "description": players_section_description,
            "externalDocs": {
                "description": "Blizzard profile pages, source of the information",
                "url": "https://overwatch.blizzard.com/en-us/search/",
            },
        },
    ],
    servers=[{"url": settings.app_base_url, "description": "Production server"}],
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    contact={
        "name": 'Valentin "TeKrop" PORCHET',
        "url": "https://github.com/TeKrop/overfast-api",
        "email": "valentin.porchet@proton.me",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/TeKrop/overfast-api/blob/main/LICENSE",
    },
    default_response_class=ASCIIJSONResponse,
)

# Mount static folder for development server
app.mount("/static", StaticFiles(directory="static"), name="static")


# Add customized OpenAPI specs with app logo
def custom_openapi() -> dict[str, Any]:  # pragma: no cover
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        description=app.description,
        version=app.version,
        contact=app.contact,
        license_info=app.license_info,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "/static/logo_light.png",
        "altText": "OverFast API Logo",
    }

    # If specified, add the "NEW" badge on new route path
    if settings.new_route_path and (
        new_route_config := openapi_schema["paths"].get(settings.new_route_path)
    ):
        new_badge = {"name": "NEW", "color": "#ff9c00"}
        for route_config in new_route_config.values():
            route_config["x-badges"] = [new_badge]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


# Add custom exception handlers for Starlette HTTP exceptions, but also
# for Pydantic Validation Errors
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    return ASCIIJSONResponse(
        content={"error": exc.detail},
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(ResponseValidationError)
async def pydantic_validation_error_handler(
    request: Request, error: ResponseValidationError
):
    raise overfast_internal_error(request.url.path, error) from error


# We need to override default Redoc page in order to be
# able to customize the favicon, same for Swagger
common_doc_settings = {
    "openapi_url": str(app.openapi_url),
    "title": f"{app.title} - Documentation",
    "favicon_url": "/static/favicon.png",
}


@app.get("/", include_in_schema=False)
async def overridden_redoc() -> HTMLResponse:
    return render_documentation(
        title=common_doc_settings["title"],
        favicon_url=common_doc_settings["favicon_url"],
        openapi_url=common_doc_settings["openapi_url"],
    )


@app.get("/docs", include_in_schema=False)
async def overridden_swagger() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=common_doc_settings["openapi_url"],
        title=common_doc_settings["title"],
        swagger_favicon_url=common_doc_settings["favicon_url"],
    )


# Add supported profiler as middleware
if settings.profiler:  # pragma: no cover
    supported_profilers = {
        Profiler.MEMRAY: MemrayInMemoryMiddleware,
        Profiler.PYINSTRUMENT: PyInstrumentMiddleware,
        Profiler.TRACEMALLOC: TraceMallocMiddleware,
        Profiler.OBJGRAPH: ObjGraphMiddleware,
    }
    if settings.profiler not in supported_profilers:
        logger.error(
            f"{settings.profiler} is not a supported profiler, please use one of the "
            f"following : {', '.join(Profiler)}"
        )
        raise SystemExit

    logger.info(f"Profiling is enabled with {settings.profiler}")
    app.add_middleware(supported_profilers[settings.profiler])  # type: ignore[arg-type]


# Add Prometheus middleware and /metrics endpoint if enabled
if settings.prometheus_enabled:
    from app.monitoring import router as monitoring_router

    register_prometheus_middleware(app)
    app.include_router(monitoring_router.router)


# Add application routers
app.include_router(heroes, prefix="/heroes")
app.include_router(roles, prefix="/roles")
app.include_router(gamemodes, prefix="/gamemodes")
app.include_router(maps, prefix="/maps")
app.include_router(players, prefix="/players")

logger.info("OverFast API... Online !")
logger.info("Version : {}", settings.app_version)
