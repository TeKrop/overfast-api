"""Heroes endpoints router : heroes list, heroes details, etc."""

from fastapi import APIRouter, Path, Query, Request, status

from app.common.decorators import validation_error_handler
from app.common.enums import HeroKey, Locale, Role, RouteTag
from app.common.helpers import routes_responses
from app.handlers.get_hero_request_handler import GetHeroRequestHandler
from app.handlers.list_heroes_request_handler import ListHeroesRequestHandler
from app.models.errors import HeroParserErrorMessage
from app.models.heroes import Hero, HeroShort

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
    request: Request,
    role: Role = Query(None, title="Role filter"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> list[HeroShort]:
    return await ListHeroesRequestHandler(request).process_request(
        role=role, locale=locale
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
        "<br />**Cache TTL : 1 day.**"
    ),
)
@validation_error_handler(response_model=Hero)
async def get_hero(
    request: Request,
    hero_key: HeroKey = Path(title="Key name of the hero"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> Hero:
    return await GetHeroRequestHandler(request).process_request(
        hero_key=hero_key, locale=locale
    )
