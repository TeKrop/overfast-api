"""Project main file containing FastAPI app and routes definitions"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.docs import setup_custom_openapi
from app.api.enums import RouteTag
from app.api.exception_handlers import register_exception_handlers
from app.api.lifespan import lifespan
from app.api.profiler import register_profiler
from app.api.responses import ASCIIJSONResponse
from app.api.routers.docs import router as docs
from app.api.routers.gamemodes import router as gamemodes
from app.api.routers.heroes import router as heroes
from app.api.routers.maps import router as maps
from app.api.routers.players import router as players
from app.api.routers.roles import router as roles
from app.config import settings
from app.infrastructure.logger import logger
from app.monitoring import router as monitoring_router
from app.monitoring.middleware import register_prometheus_middleware

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

# Setup FastAPI generic stuff and docs
setup_custom_openapi(app, new_route_path=settings.new_route_path)
register_exception_handlers(app)

# Add supported profiler as middleware
if settings.profiler:  # pragma: no cover
    register_profiler(app, settings.profiler)


# Add Prometheus middleware and /metrics endpoint if enabled
if settings.prometheus_enabled:
    register_prometheus_middleware(app)
    app.include_router(monitoring_router.router)


# Add application routers
app.include_router(docs)
app.include_router(heroes, prefix="/heroes")
app.include_router(roles, prefix="/roles")
app.include_router(gamemodes, prefix="/gamemodes")
app.include_router(maps, prefix="/maps")
app.include_router(players, prefix="/players")

logger.info("OverFast API... Online !")
logger.info("Version : {}", settings.app_version)
