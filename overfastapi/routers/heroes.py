"""Heroes endpoints router : heroes list, heroes details, roles list, etc."""

from fastapi import APIRouter, BackgroundTasks, Path, Query, Request

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import HeroKey, Role
from overfastapi.common.helpers import routes_responses
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
@validation_error_handler(response_model=HeroShort)
async def list_heroes(
    background_tasks: BackgroundTasks,
    request: Request,
    role: Role | None = Query(None, title="Role filter"),
):
    return ListHeroesRequestHandler(request).process_request(
        background_tasks=background_tasks, role=role
    )


@router.get(
    "/roles",
    response_model=list[RoleDetail],
    responses=routes_responses,
    tags=["Heroes"],
    summary="Get a list of roles",
    description=("Get a list of available Overwatch roles"),
)
@validation_error_handler(response_model=RoleDetail)
async def list_roles(background_tasks: BackgroundTasks, request: Request):
    return ListRolesRequestHandler(request).process_request(
        background_tasks=background_tasks
    )


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
@validation_error_handler(response_model=Hero)
async def get_hero(
    background_tasks: BackgroundTasks,
    request: Request,
    hero_key: HeroKey = Path(title="Key name of the hero"),
):
    return GetHeroRequestHandler(request).process_request(
        background_tasks=background_tasks, hero_key=hero_key
    )
