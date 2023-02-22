"""Heroes endpoints router : heroes list, heroes details, etc."""

from fastapi import APIRouter, BackgroundTasks, Path, Query, Request

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import HeroKey, Locale, Role, RouteTag
from overfastapi.common.helpers import routes_responses
from overfastapi.handlers.get_hero_request_handler import GetHeroRequestHandler
from overfastapi.handlers.list_heroes_request_handler import ListHeroesRequestHandler
from overfastapi.models.heroes import Hero, HeroShort

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of heroes",
    description=(
        "Get a list of Overwatch heroes, which can be filtered using roles. "
        "<br />**Cache TTL : 1 day.**"
    ),
)
@validation_error_handler(response_model=HeroShort)
async def list_heroes(
    background_tasks: BackgroundTasks,
    request: Request,
    role: Role | None = Query(None, title="Role filter"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> list[HeroShort]:
    return await ListHeroesRequestHandler(request).process_request(
        background_tasks=background_tasks, role=role, locale=locale
    )


@router.get(
    "/{hero_key}",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get hero data",
    description=(
        "Get data about an Overwatch hero : description, abilities, story, etc. "
        "<br />**Cache TTL : 1 day.**"
    ),
)
@validation_error_handler(response_model=Hero)
async def get_hero(
    background_tasks: BackgroundTasks,
    request: Request,
    hero_key: HeroKey = Path(title="Key name of the hero"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> Hero:
    return await GetHeroRequestHandler(request).process_request(
        background_tasks=background_tasks, hero_key=hero_key, locale=locale
    )
