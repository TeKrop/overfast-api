"""Project main file containing FastAPI app and routes definitions"""

from collections.abc import Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .enums import RouteTag
from .gamemodes import router as gamemodes
from .helpers import overfast_internal_error
from .heroes import router as heroes
from .maps import router as maps
from .overfast_client import OverFastClient
from .overfast_logger import logger
from .players import router as players
from .players.commands.update_search_data_cache import update_search_data_cache
from .roles import router as roles

# pyinstrument won't be installed on production, that's why we're checking it here
with suppress(ModuleNotFoundError):
    from pyinstrument import Profiler


@asynccontextmanager
async def lifespan(_: FastAPI):  # pragma: no cover
    # Update search data list from Blizzard before starting up
    logger.info("Updating search data cache (avatars, namecards, titles)")
    with suppress(SystemExit):
        update_search_data_cache()

    # Instanciate HTTPX Async Client
    logger.info("Instanciating HTTPX AsyncClient...")
    overfast_client = OverFastClient()

    yield

    # Properly close HTTPX Async Client
    await overfast_client.aclose()


app = FastAPI(title="OverFast API", docs_url=None, redoc_url=None, lifespan=lifespan)
description = f"""OverFast API provides comprehensive data on Overwatch 2 heroes,
game modes, maps, and player statistics by scraping Blizzard pages. Developed with
the efficiency of **FastAPI** and **Beautiful Soup**, it leverages **nginx** as a
reverse proxy and **Redis** for caching. Its tailored caching mechanism significantly
reduces calls to Blizzard pages, ensuring swift and precise data delivery to users.

This live instance is configured with the following restrictions:
- Rate Limit per IP: **{settings.rate_limit_per_second_per_ip} requests/second** (burst capacity :
**{settings.rate_limit_per_ip_burst}**)
- Maximum connections/simultaneous requests per IP: **{settings.max_connections_per_ip}**
- Retry delay after Blizzard rate limiting: **{settings.blizzard_rate_limit_retry_after} seconds**

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


def custom_openapi():  # pragma: no cover
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="OverFast API",
        description=description,
        version=settings.app_version,
        contact={
            "name": 'Valentin "TeKrop" PORCHET',
            "url": "https://github.com/TeKrop/overfast-api",
            "email": "valentin.porchet@proton.me",
        },
        license_info={
            "name": "MIT",
            "url": "https://github.com/TeKrop/overfast-api/blob/main/LICENSE",
        },
        routes=app.routes,
        tags=[
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
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://files.tekrop.fr/overfast_api_logo_full_1000.png",
        "altText": "OverFast API Logo",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.mount("/static", StaticFiles(directory="static"), name="static")

app.logger = logger
logger.info("OverFast API... Online !")
logger.info("Version : {}", settings.app_version)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    return JSONResponse(
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
    "openapi_url": app.openapi_url,
    "title": f"{app.title} - Documentation",
    "favicon_url": "/static/favicon.png",
}


@app.get("/", include_in_schema=False)
async def overridden_redoc():
    redoc_settings = common_doc_settings.copy()
    redoc_settings["redoc_favicon_url"] = redoc_settings.pop("favicon_url")
    return get_redoc_html(**redoc_settings)


@app.get("/docs", include_in_schema=False)
async def overridden_swagger():
    swagger_settings = common_doc_settings.copy()
    swagger_settings["swagger_favicon_url"] = swagger_settings.pop("favicon_url")
    return get_swagger_ui_html(**swagger_settings)


# In case enabled in settings, add the pyinstrument profiler middleware
if settings.profiling is True:
    logger.info("Profiling is enabled")

    @app.middleware("http")
    async def profile_request(request: Request, call_next: Callable):
        """Profile the current request"""
        # if the `profile=true` HTTP query argument is passed, we profile the request
        if request.query_params.get("profile", False):
            # we profile the request along with all additional middlewares, by interrupting
            # the program every 1ms1 and records the entire stack at that point
            with Profiler(interval=0.001, async_mode="enabled") as profiler:
                await call_next(request)

            # we dump the profiling into a file
            return HTMLResponse(profiler.output_html())

        # Proceed without profiling
        return await call_next(request)


# Add application routers
app.include_router(heroes.router, prefix="/heroes")
app.include_router(roles.router, prefix="/roles")
app.include_router(gamemodes.router, prefix="/gamemodes")
app.include_router(maps.router, prefix="/maps")
app.include_router(players.router, prefix="/players")
