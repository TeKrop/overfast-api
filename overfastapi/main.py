# pylint: disable=R0913,C0103,C0116,W0613
"""Project main file containing FastAPI app and routes definitions"""

from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Path, Query, Request, status
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from overfastapi.common.enums import (
    HeroKey,
    MapGamemode,
    PlayerAchievementCategory,
    PlayerGamemode,
    PlayerPlatform,
    PlayerPrivacy,
    Role,
)
from overfastapi.common.helpers import overfast_internal_error
from overfastapi.common.logging import logger
from overfastapi.config import OVERFAST_API_VERSION
from overfastapi.handlers.get_hero_request_handler import GetHeroRequestHandler
from overfastapi.handlers.get_player_career_request_handler import (
    GetPlayerCareerRequestHandler,
)
from overfastapi.handlers.list_heroes_request_handler import ListHeroesRequestHandler
from overfastapi.handlers.list_map_gamemodes_request_handler import (
    ListMapGamemodesRequestHandler,
)
from overfastapi.handlers.list_maps_request_handler import ListMapsRequestHandler
from overfastapi.handlers.search_players_request_handler import (
    SearchPlayersRequestHandler,
)
from overfastapi.models.errors import (
    BlizzardErrorMessage,
    InternalServerErrorMessage,
    ParserInitErrorMessage,
)
from overfastapi.models.heroes import Hero, HeroShort
from overfastapi.models.maps import Map, MapGamemodeDetails
from overfastapi.models.players import (
    CareerStats,
    Player,
    PlayerAchievementsContainer,
    PlayerSearchResult,
    PlayerSummary,
)

app = FastAPI(
    title="OverFast API",
    docs_url=None,
    redoc_url=None,
)
description = """OverFast API gives data about Overwatch heroes, maps, and players statistics by
scraping Blizzard pages. It was built with **FastAPI** and **Beautiful Soup**, and uses **nginx**
as reverse proxy and **Redis** for caching. By using a specific cache system, it minimizes
calls to Blizzard pages (which can be very slow), and quickly returns accurate data to users.

## Cache System

![Python + Redis + Nginx](https://files.tekrop.fr/classic_schema_nginx_cache.png)

### Functioning

OverFast API introduces a very specific cache system, stored on a **Redis** server, and divided in two parts :
* **API Cache** : a very high level cache, linking URIs (cache key) to raw JSON data. When first doing a request, if a cache is available, the JSON data is returned as-is by the **nginx** server. The cached values are stored with an arbitrary TTL (time to leave) parameter depending on the called route.
* **Parser Cache** : a specific cache for the parser system of the OverFast API. When an HTML Blizzard page is parsed, we store the MD5 hash of the HTML content and the parsing result (as a JSON string), in order to minimize the heavy parsing process if the page hasn't changed since the last API call. There is no TTL on this cache.

### API Cache TTL values
* Heroes list : 1 day
* Hero specific data : 1 day
* Maps list : 1 day
* Maps gamemodes list : 1 day
* Players career : 30 minutes
* Players search : 1 hour

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
                    "url": "https://playoverwatch.com/en-us/heroes/",
                },
            },
            {
                "name": "Maps",
                "description": "Overwatch maps details",
                "externalDocs": {
                    "description": "Blizzard maps page, source of the information",
                    "url": "https://playoverwatch.com/en-us/maps/",
                },
            },
            {
                "name": "Players",
                "description": "Overwatch players data : level, statistics, achievements, etc.",
                "externalDocs": {
                    "description": "Blizzard profile pages, source of the information",
                    "url": "https://playoverwatch.com/en-us/search/",
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

routes_responses = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": InternalServerErrorMessage,
        "description": "Internal Server Error",
    },
    status.HTTP_504_GATEWAY_TIMEOUT: {
        "model": BlizzardErrorMessage,
        "description": "Blizzard Server Error",
    },
}

player_career_routes_responses = {
    status.HTTP_404_NOT_FOUND: {
        "model": ParserInitErrorMessage,
        "description": "Player Not Found",
    },
    **routes_responses,
}


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


@app.get(
    "/heroes",
    response_model=list[HeroShort],
    responses=routes_responses,
    tags=["Heroes"],
    summary="Get a list of heroes",
    description="Get a list of Overwatch heroes, which can be filtered using roles",
)
async def list_heroes(
    background_tasks: BackgroundTasks,
    request: Request,
    role: Optional[Role] = Query(None, title="Role filter"),
):
    heroes_list = ListHeroesRequestHandler(request).process_request(
        background_tasks=background_tasks, role=role
    )
    try:
        return [HeroShort(**hero) for hero in heroes_list]
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/heroes/{hero_key}",
    response_model=Hero,
    responses=routes_responses,
    tags=["Heroes"],
    summary="Get detailed data about a specific hero",
    description=(
        "Get details data about a specific Overwatch hero : "
        "weapons, abilities, story, medias, etc."
    ),
)
async def get_hero(
    background_tasks: BackgroundTasks,
    request: Request,
    hero_key: HeroKey = Path(
        ...,
        title="Key name of the hero",
    ),
):
    hero_details = GetHeroRequestHandler(request).process_request(
        background_tasks=background_tasks, hero_key=hero_key
    )
    try:
        return Hero(**hero_details)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/maps",
    response_model=list[Map],
    responses=routes_responses,
    tags=["Maps"],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps, which can be filtered "
        "by gamemodes they can be played on"
    ),
)
async def list_maps(
    background_tasks: BackgroundTasks,
    request: Request,
    gamemode: Optional[MapGamemode] = Query(
        None,
        title="Map Gamemode",
        description="Filter maps playable on a specific gamemode.",
    ),
):
    maps_list = ListMapsRequestHandler(request).process_request(
        background_tasks=background_tasks, gamemode=gamemode
    )
    try:
        return [Map(**ow_map) for ow_map in maps_list]
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/maps/gamemodes",
    response_model=list[MapGamemodeDetails],
    responses=routes_responses,
    tags=["Maps"],
    summary="Get a list of maps gamemodes",
    description="Get a list of Overwatch maps gamemodes : Assault, Escort, Hybrid, etc.",
)
async def list_map_gamemodes(
    background_tasks: BackgroundTasks,
    request: Request,
):
    gamemodes = ListMapGamemodesRequestHandler(request).process_request(
        background_tasks=background_tasks
    )
    try:
        return [MapGamemodeDetails(**gamemode) for gamemode in gamemodes]
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/players",
    response_model=PlayerSearchResult,
    responses=routes_responses,
    tags=["Players"],
    summary="Search for a specific player",
)
async def search_players(
    request: Request,
    name: str = Query(
        ...,
        title="Player nickname to search",
        example="TeKrop",
    ),
    min_level: Optional[int] = Query(
        None, title="Minimum level of the player (included)", example=42, gt=0
    ),
    max_level: Optional[int] = Query(
        None, title="Maximum level of the player (included)", example=42, gt=0
    ),
    platform: Optional[PlayerPlatform] = Query(
        None, title="Platform on which the player is", example="pc"
    ),
    privacy: Optional[PlayerPrivacy] = Query(
        None, title="Privacy settings of the player career", example="public"
    ),
    order_by: Optional[str] = Query(
        "name:asc",
        title="Ordering field and the way it's arranged (asc[ending]/desc[ending])",
        regex="^(player_id|name|level|platform|privacy):(asc|desc)$",
    ),
    offset: Optional[int] = Query(0, title="Offset of the results", ge=0),
    limit: Optional[int] = Query(20, title="Limit of results per page", gt=0),
):
    player_search_result = SearchPlayersRequestHandler(request).process_request(
        name=name,
        min_level=min_level,
        max_level=max_level,
        privacy=privacy,
        platform=platform,
        order_by=order_by,
        offset=offset,
        limit=limit,
    )
    try:
        return PlayerSearchResult(**player_search_result)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


async def get_player_common_parameters(
    platform: PlayerPlatform = Path(
        ..., title="Platform on which the player is", example="pc"
    ),
    player_id: str = Path(
        ...,
        title="Player unique name",
        description=(
            'Identifier of the player : BattleTag (with "#" replaced by "-") for '
            "PC players, nickname for PSN/XBL players, nickname followed by "
            "hexadecimal id for Nintendo Switch."
        ),
        example="TeKrop-2217",
    ),
):
    return {"platform": platform, "player_id": player_id}


@app.get(
    "/players/{platform}/{player_id}",
    response_model=Player,
    responses=player_career_routes_responses,
    tags=["Players"],
    summary="Get player career data",
    description="Get all player data : summary, statistics and achievements",
)
async def get_player_career(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
):
    player_career = GetPlayerCareerRequestHandler(request).process_request(
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
    )
    try:
        return Player(**player_career)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/players/{platform}/{player_id}/summary",
    response_model=PlayerSummary,
    responses=player_career_routes_responses,
    tags=["Players"],
    summary="Get player summary",
)
async def get_player_summary(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
):
    player_summary = GetPlayerCareerRequestHandler(request).process_request(
        summary=True,
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
    )
    try:
        return PlayerSummary(**player_summary)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/players/{platform}/{player_id}/stats",
    response_model=CareerStats,
    response_model_exclude_unset=True,
    responses=player_career_routes_responses,
    tags=["Players"],
    summary="Get player statistics about heroes",
    description=(
        "Career contains numerous statistics "
        "grouped by heroes and categories (combat, game, best, hero specific, "
        "average, etc.), while heroes comparisons contains generic details grouped "
        "by main categories (time played, games won, objective kills, etc.)"
    ),
)
async def get_player_stats(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
    gamemode: PlayerGamemode = Query(
        ...,
        title="Gamemode",
        description="Filter on a specific gamemode.",
    ),
    hero: Optional[HeroKey] = Query(
        None,
        title="Hero key",
        description="Filter on a specific hero in order to only get his statistics.",
    ),
):
    player_career_stats = GetPlayerCareerRequestHandler(request).process_request(
        stats=True,
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
        gamemode=gamemode,
        hero=hero,
    )
    try:
        return CareerStats(**player_career_stats)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@app.get(
    "/players/{platform}/{player_id}/achievements",
    response_model=PlayerAchievementsContainer,
    response_model_exclude_unset=True,
    responses=player_career_routes_responses,
    tags=["Players"],
    summary="Get player achievements",
)
async def get_player_achievements(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
    category: Optional[PlayerAchievementCategory] = Query(
        None,
        title="Achievements category",
        description="Filter on specific achievements category",
    ),
):
    player_achievements = GetPlayerCareerRequestHandler(request).process_request(
        achievements=True,
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
        category=category,
    )
    try:
        return PlayerAchievementsContainer(**player_achievements)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error
