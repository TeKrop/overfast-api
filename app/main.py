"""Project main file containing FastAPI app and routes definitions"""

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .enums import Profiler, RouteTag
from .gamemodes import router as gamemodes
from .helpers import overfast_internal_error
from .heroes import router as heroes
from .maps import router as maps
from .middlewares import (
    MemrayInMemoryMiddleware,
    ObjGraphMiddleware,
    PyInstrumentMiddleware,
    TraceMallocMiddleware,
)
from .overfast_client import OverFastClient
from .overfast_logger import logger
from .players import router as players
from .roles import router as roles


@asynccontextmanager
async def lifespan(_: FastAPI):  # pragma: no cover
    # Instanciate HTTPX Async Client
    logger.info("Instanciating HTTPX AsyncClient...")
    overfast_client = OverFastClient()

    yield

    # Properly close HTTPX Async Client
    await overfast_client.aclose()


description = f"""OverFast API provides comprehensive data on Overwatch 2 heroes,
game modes, maps, and player statistics by scraping Blizzard pages. Developed with
the efficiency of **FastAPI** and **Selectolax**, it leverages **nginx (OpenResty)** as a
reverse proxy and **Valkey** for caching. Its tailored caching mechanism significantly
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

# Add customized OpenAPI specs with app logo


def custom_openapi():  # pragma: no cover
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
        "url": "/static/logo.png",
        "altText": "OverFast API Logo",
    }

    # If specified, add the "New" badge on new route path
    if settings.new_route_path and (
        new_route_config := openapi_schema["paths"].get(settings.new_route_path)
    ):
        new_badge = {"name": "New", "color": "#00bfae"}
        for route_config in new_route_config.values():
            route_config["x-badges"] = [new_badge]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add custom exception handlers for Starlet HTTP exceptions, but also
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
    app.add_middleware(supported_profilers[settings.profiler])

# Add application routers
app.include_router(heroes.router, prefix="/heroes")
app.include_router(roles.router, prefix="/roles")
app.include_router(gamemodes.router, prefix="/gamemodes")
app.include_router(maps.router, prefix="/maps")
app.include_router(players.router, prefix="/players")

logger.info("OverFast API... Online !")
logger.info("Version : {}", settings.app_version)
