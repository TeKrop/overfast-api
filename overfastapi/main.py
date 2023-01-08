"""Project main file containing FastAPI app and routes definitions"""

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from overfastapi.common.enums import RouteTag
from overfastapi.common.logging import logger
from overfastapi.config import OVERFAST_API_VERSION
from overfastapi.routers import gamemodes, heroes, players, roles

app = FastAPI(
    title="OverFast API",
    docs_url=None,
    redoc_url=None,
)
description = """OverFast API gives data about Overwatch 2 heroes, gamemodes, and players
statistics by scraping Blizzard pages. Built with **FastAPI** and **Beautiful Soup**, and uses
**nginx** as reverse proxy and **Redis** for caching. By using a specific cache system, it
minimizes calls to Blizzard pages (which can be very slow), and quickly returns accurate
data to users. All duration values are also returned in seconds for convenience.

## 👷 W.I.P. 👷

- Various improvements on caching system
- Translations for specific heroes pages (will be available using a query parameter)
- Additional data about gamemodes and maps
"""


def custom_openapi():  # pragma: no cover
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="OverFast API",
        description=description,
        version=OVERFAST_API_VERSION,
        contact={
            "name": 'Valentin "TeKrop" PORCHET',
            "url": "https://github.com/TeKrop/overfast-api",
            "email": "vporchet@gmail.com",
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
                "name": RouteTag.PLAYERS,
                "description": "Overwatch players data : summary, statistics, etc.",
                "externalDocs": {
                    "description": "Blizzard profile pages, source of the information",
                    "url": "https://overwatch.blizzard.com/en-us/search/",
                },
            },
        ],
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://files.tekrop.fr/overfast_api_logo_full_1000.png",
        "altText": "OverFast API Logo",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.logger = logger
logger.info("OverFast API... Online !")
logger.info("Version : {}", OVERFAST_API_VERSION)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(content={"error": exc.detail}, status_code=exc.status_code)


# We need to override default Redoc page in order to be
# able to customize the favicon...
@app.get("/", include_in_schema=False)
def overridden_redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="OverFast API - Documentation",
        redoc_favicon_url="/favicon.png",
    )


# Add application routers
app.include_router(heroes.router, prefix="/heroes")
app.include_router(roles.router, prefix="/roles")
app.include_router(gamemodes.router, prefix="/gamemodes")
app.include_router(players.router, prefix="/players")
