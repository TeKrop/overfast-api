"""Heroes endpoints router : heroes list, heroes details, etc."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request, Response, status

from app.enums import Locale, RouteTag
from app.helpers import routes_responses
from app.heroes.controllers.get_hero_controller import GetHeroController
from app.heroes.controllers.get_hero_stats_summary_controller import (
    GetHeroStatsSummaryController,
)
from app.heroes.controllers.list_heroes_controller import ListHeroesController
from app.heroes.enums import HeroGamemode, HeroKey
from app.heroes.models import (
    BadRequestErrorMessage,
    Hero,
    HeroParserErrorMessage,
    HeroShort,
    HeroStatsSummary,
)
from app.maps.enums import MapKey
from app.players.enums import (
    CompetitiveDivisionFilter,
    PlayerGamemode,
    PlayerPlatform,
    PlayerRegion,
)
from app.roles.enums import Role

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of heroes",
    description=(
        "Get a list of Overwatch heroes, which can be filtered using roles or gamemodes. "
        f"<br />**Cache TTL : {ListHeroesController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_heroes",
    response_model=list[HeroShort],
)
async def list_heroes(
    request: Request,
    response: Response,
    role: Annotated[Role | None, Query(title="Role filter")] = None,
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
    gamemode: Annotated[HeroGamemode | None, Query(title="Gamemode filter")] = None,
) -> Any:
    return await ListHeroesController(request, response).process_request(
        role=role,
        locale=locale,
        gamemode=gamemode,
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
    summary="Get hero stats",
    description=(
        "Get hero statistics usage, filtered by platform, region, role, etc."
        "Only Role Queue gamemodes are concerned."
        f"<br />**Cache TTL : {GetHeroStatsSummaryController.get_human_readable_timeout()}.**"
    ),
    operation_id="get_hero_stats",
    response_model=list[HeroStatsSummary],
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
        MapKey | None, Query(alias="map", title="Map key filter", examples=["hanaoka"])  # ty: ignore[invalid-type-form]
    ] = None,
    competitive_division: Annotated[
        CompetitiveDivisionFilter | None,  # ty: ignore[invalid-type-form]
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
) -> Any:
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
        "Get data about an Overwatch hero : description, abilities, stadium powers, story, etc. "
        f"<br />**Cache TTL : {GetHeroController.get_human_readable_timeout()}.**"
    ),
    operation_id="get_hero",
    response_model=Hero,
)
async def get_hero(
    request: Request,
    response: Response,
    hero_key: Annotated[HeroKey, Path(title="Key name of the hero")],  # ty: ignore[invalid-type-form]
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> Any:
    return await GetHeroController(request, response).process_request(
        hero_key=hero_key,
        locale=locale,
    )
