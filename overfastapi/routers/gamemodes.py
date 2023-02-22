"""Gamemodes endpoints router : gamemodes list, etc."""
from fastapi import APIRouter, BackgroundTasks, Query, Request

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import Locale, RouteTag
from overfastapi.common.helpers import routes_responses
from overfastapi.handlers.list_gamemodes_request_handler import (
    ListGamemodesRequestHandler,
)
from overfastapi.models.gamemodes import GamemodeDetails

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.GAMEMODES],
    summary="Get a list of gamemodes",
    description=(
        "Get a list of Overwatch gamemodes : Assault, Escort, Hybrid, etc."
        "<br />**Cache TTL : 1 day.**"
    ),
)
@validation_error_handler(response_model=GamemodeDetails)
async def list_map_gamemodes(
    background_tasks: BackgroundTasks,
    request: Request,
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> list[GamemodeDetails]:
    return await ListGamemodesRequestHandler(request).process_request(
        background_tasks=background_tasks, locale=locale
    )
