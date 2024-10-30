"""Heroes endpoints router : heroes list, heroes details, etc."""

from fastapi import APIRouter, Path, Query, Request, status

from app.decorators import validation_error_handler
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
@validation_error_handler(response_model=HeroShort)
async def list_heroes(
    request: Request,
    role: Role = Query(None, title="Role filter"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
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
@validation_error_handler(response_model=Hero)
async def get_hero(
    request: Request,
    hero_key: HeroKey = Path(title="Key name of the hero"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> Hero:
    return await GetHeroController(request).process_request(
        hero_key=hero_key,
        locale=locale,
    )
