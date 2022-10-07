from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Path, Query, Request

from overfastapi.common.enums import HeroKey, Role
from overfastapi.common.helpers import routes_responses, value_with_validation_check
from overfastapi.handlers.get_hero_request_handler import GetHeroRequestHandler
from overfastapi.handlers.list_heroes_request_handler import ListHeroesRequestHandler
from overfastapi.handlers.list_roles_request_handler import ListRolesRequestHandler
from overfastapi.models.heroes import Hero, HeroShort, RoleDetail


router = APIRouter()


@router.get(
    "",
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
    return value_with_validation_check([HeroShort(**hero) for hero in heroes_list])


@router.get(
    "/roles",
    response_model=list[RoleDetail],
    responses=routes_responses,
    tags=["Heroes"],
    summary="Get a list of roles",
    description=("Get a list of available Overwatch roles"),
)
async def get_roles(background_tasks: BackgroundTasks, request: Request):
    roles_list = ListRolesRequestHandler(request).process_request(
        background_tasks=background_tasks
    )
    return value_with_validation_check([RoleDetail(**role) for role in roles_list])


@router.get(
    "/{hero_key}",
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
    return value_with_validation_check(Hero(**hero_details))
