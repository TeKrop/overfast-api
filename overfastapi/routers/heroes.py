# pylint: disable=R0913,C0116
"""Heroes endpoints router : heroes list, heroes details, roles list, etc."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Path, Query, Request
from pydantic import ValidationError

from overfastapi.common.enums import HeroKey, Role
from overfastapi.common.helpers import overfast_internal_error, routes_responses
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
    try:
        return [HeroShort(**hero) for hero in heroes_list]
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


@router.get(
    "/roles",
    response_model=list[RoleDetail],
    responses=routes_responses,
    tags=["Heroes"],
    summary="Get a list of roles",
    description=("Get a list of available Overwatch roles"),
)
async def list_roles(background_tasks: BackgroundTasks, request: Request):
    roles_list = ListRolesRequestHandler(request).process_request(
        background_tasks=background_tasks
    )
    try:
        return [RoleDetail(**role) for role in roles_list]
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error


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
    try:
        return Hero(**hero_details)
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error
