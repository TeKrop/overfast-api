"""Heroes endpoints router : heroes list, heroes details, etc."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, status

from app.enums import Locale, RouteTag
from app.helpers import routes_responses
from app.roles.enums import Role

from .controllers.get_hero_controller import GetHeroController
from .controllers.list_heroes_controller import ListHeroesController
from .enums import HeroKey
from .models import Hero, HeroParserErrorMessage, HeroShort

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
    role: Annotated[Role | None, Query(title="Role filter")] = None,
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> list[HeroShort]:
    return await ListHeroesController(request).process_request(
        role=role,
        locale=locale,
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
    hero_key: Annotated[HeroKey, Path(title="Key name of the hero")],
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> Hero:
    return await GetHeroController(request).process_request(
        hero_key=hero_key,
        locale=locale,
    )
