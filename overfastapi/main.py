"""Project main file containing FastAPI app and routes definitions"""

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from overfastapi.common.logging import logger
from overfastapi.config import OVERFAST_API_VERSION
from overfastapi.routers import gamemodes, heroes

app = FastAPI(
    title="OverFast API",
    docs_url=None,
    redoc_url=None,
)
description = """OverFast API gives data about Overwatch heroes, gamemodes, and (soon) players
statistics by scraping Blizzard pages. Built with **FastAPI** and **Beautiful Soup**, and uses
**nginx** as reverse proxy and **Redis** for caching. By using a specific cache system, it
minimizes calls to Blizzard pages (which can be very slow), and quickly returns accurate
data to users.

## 🚧 Work in progress 🚧

I'm currently rewriting the API for Overwatch 2, by scrapping new Blizzard pages.
So far, here is the progress :
- Heroes list : ✅
- Hero specific data : ✅
- Roles list : ✅
- Gamemodes list : ✅
- Players career : 👷 (working on it, Blizzard pages are back since season 2 update)
- Players search : 👷 (working on it, Blizzard pages are back since season 2 update)

## Cache System

![Python + Redis + Nginx](https://files.tekrop.fr/classic_schema_nginx_cache.svg)

### Functioning

OverFast API introduces a very specific cache system, stored on a **Redis** server, and divided in two parts :
* **API Cache** : a very high level cache, linking URIs (cache key) to raw JSON data. When first doing a request, if a cache is available, the JSON data is returned as-is by the **nginx** server. The cached values are stored with an arbitrary TTL (time to leave) parameter depending on the called route.
* **Parser Cache** : a specific cache for the parser system of the OverFast API. When an HTML Blizzard page is parsed, a hash of the HTML content and the parsing result (as a JSON string) are stored, in order to minimize the heavy parsing process if the page hasn't changed since the last API call. There is no TTL on this cache.

### API Cache TTL values
* Heroes list : 1 day
* Hero specific data : 1 day
* Roles list : 1 day
* Gamemodes list : 1 day

### Automatic cache refresh

In order to reduce the number of requests to Blizzard that API users can make,
I introduced a specific cache refresh system. The main idea is to update the API Cache
in the background (server side) when needed, just before its expiration. For example,
if a user requests its player career page, it will be slow for the first call
(2-3s in total), but very fast for all the next times, thanks to this system."""


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
                "name": "Heroes",
                "description": "Overwatch heroes details : lore, abilities, etc.",
                "externalDocs": {
                    "description": "Blizzard heroes page, source of the information",
                    "url": "https://overwatch.blizzard.com/en-us/heroes/",
                },
            },
            {
                "name": "Maps",
                "description": "Overwatch maps details",
                "externalDocs": {
                    "description": "Overwatch home page, source of the information",
                    "url": "https://overwatch.blizzard.com/en-us/",
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
app.include_router(gamemodes.router, prefix="/gamemodes")
