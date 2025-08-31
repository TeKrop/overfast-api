"""Heroes endpoints router : heroes list, heroes details, etc."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response, status

from app.enums import Locale, RouteTag
from app.helpers import routes_responses
from app.maps.enums import MapKey
from app.players.enums import (
    CompetitiveDivisionFilter,
    PlayerGamemode,
    PlayerPlatform,
    PlayerRegion,
)
from app.roles.enums import Role

from .controllers.get_hero_controller import GetHeroController
from .controllers.get_hero_stats_summary_controller import GetHeroStatsSummaryController
from .controllers.list_heroes_controller import ListHeroesController
from .enums import HeroKey
from .models import (
    BadRequestErrorMessage,
    Hero,
    HeroParserErrorMessage,
    HeroShort,
    HeroStatsSummary,
)

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of heroes",
    description=(
        "Get a list of Overwatch heroes, which can be filtered using roles. "
        f"<br />**Cache TTL : {ListHeroesController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_heroes",
)
async def list_heroes(
    request: Request,
    response: Response,
    role: Annotated[Role | None, Query(title="Role filter")] = None,
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> list[HeroShort]:
    return await ListHeroesController(request, response).process_request(
        role=role,
        locale=locale,
    )


@router.get(
    "/stats",
    responses={
        **routes_responses,
        status.HTTP_400_BAD_REQUEST: {
            "model": BadRequestErrorMessage,
            "description": "Bad Request Error",
        },
    },
    tags=[RouteTag.HEROES],
    summary="Get hero statistics",
    description=(
        "Get hero statistics usage, filtered by platform, region, role, etc."
        "Only Role Queue gamemodes are concerned."
        f"<br />**Cache TTL : {GetHeroStatsSummaryController.get_human_readable_timeout()}.**"
    ),
    operation_id="get_hero_stats",
)
async def get_hero_stats(
    request: Request,
    response: Response,
    platform: Annotated[
        PlayerPlatform, Query(title="Player platform filter", examples=["pc"])
    ],
    gamemode: Annotated[
        PlayerGamemode,
        Query(
            title="Gamemode",
            description=("Filter on a specific gamemode."),
            examples=["competitive"],
        ),
    ],
    region: Annotated[
        PlayerRegion,
        Query(
            title="Region",
            description=("Filter on a specific player region."),
            examples=["europe"],
        ),
    ],
    role: Annotated[
        Role | None, Query(title="Role filter", examples=["support"])
    ] = None,
    map_: Annotated[
        MapKey | None, Query(alias="map", title="Map key filter", examples=["hanaoka"])
    ] = None,
    competitive_division: Annotated[
        CompetitiveDivisionFilter | None,
        Query(
            title="Competitive division filter",
            examples=["diamond"],
        ),
    ] = None,
    order_by: Annotated[
        str,
        Query(
            title="Ordering field and the way it's arranged (asc[ending]/desc[ending])",
            pattern=r"^(hero|winrate|pickrate):(asc|desc)$",
        ),
    ] = "hero:asc",
) -> list[HeroStatsSummary]:
    return await GetHeroStatsSummaryController(request, response).process_request(
        platform=platform,
        gamemode=gamemode,
        region=region,
        role=role,
        map=map_,
        competitive_division=competitive_division,
        order_by=order_by,
    )


@router.get(
    "/{hero_key}",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": HeroParserErrorMessage,
            "description": "Hero Not Found",
        },
        **routes_responses,
    },
    tags=[RouteTag.HEROES],
    summary="Get hero data",
    description=(
        "Get data about an Overwatch hero : description, abilities, story, etc. "
        f"<br />**Cache TTL : {GetHeroController.get_human_readable_timeout()}.**"
    ),
    operation_id="get_hero",
)
async def get_hero(
    request: Request,
    response: Response,
    hero_key: Annotated[HeroKey, Path(title="Key name of the hero")],
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> Hero:
    return await GetHeroController(request, response).process_request(
        hero_key=hero_key,
        locale=locale,
    )
