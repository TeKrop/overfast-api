"""Project main file containing FastAPI app and routes definitions"""
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .commands.update_search_data_cache import update_search_data_cache
from .common.enums import RouteTag
from .common.logging import logger
from .config import settings
from .routers import gamemodes, heroes, maps, players, roles


@asynccontextmanager
async def lifespan(_: FastAPI):  # pragma: no cover
    # Update search data list from Blizzard before starting up
    if settings.redis_caching_enabled:
        logger.info("Updating search data cache (avatars, namecards, titles)")
        with suppress(SystemExit):
            update_search_data_cache()

    yield


app = FastAPI(title="OverFast API", docs_url=None, redoc_url=None, lifespan=lifespan)
description = f"""OverFast API provides comprehensive data on Overwatch 2 heroes,
game modes, maps, and player statistics by scraping Blizzard pages. Developed with
the efficiency of **FastAPI** and **Beautiful Soup**, it leverages **nginx** as a
reverse proxy and **Redis** for caching. Its tailored caching mechanism significantly
reduces calls to Blizzard pages, ensuring swift and precise data delivery to users.

This live instance is restricted to **30 req/s** (a shared limit across all endpoints).
If you require more, consider hosting your own instance on a server 👍

In player career statistics, various conversions are applied for ease of use:
- **Duration values** are converted to **seconds** (integer)
- **Percent values** are represented as **integers**, omitting the percent symbol
- Integer and float string representations are converted to their respective types

Swagger UI (useful for trying API calls) : {settings.app_base_url}/docs

{f"Status page : {settings.status_page_url}" if settings.status_page_url else ""}
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
                "description": "Overwatch players data : summary, statistics, etc.",
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
    return JSONResponse(content={"error": exc.detail}, status_code=exc.status_code)


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


# Add application routers
app.include_router(heroes.router, prefix="/heroes")
app.include_router(roles.router, prefix="/roles")
app.include_router(gamemodes.router, prefix="/gamemodes")
app.include_router(maps.router, prefix="/maps")
app.include_router(players.router, prefix="/players")
