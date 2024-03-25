"""Gamemodes endpoints router : gamemodes list, etc."""

from fastapi import APIRouter, Request

from app.common.decorators import validation_error_handler
from app.common.enums import RouteTag
from app.common.helpers import routes_responses
from app.handlers.list_gamemodes_request_handler import ListGamemodesRequestHandler
from app.models.gamemodes import GamemodeDetails

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.GAMEMODES],
    summary="Get a list of gamemodes",
    description=(
        "Get a list of Overwatch gamemodes : Assault, Escort, Flashpoint, Hybrid, etc."
        "<br />**Cache TTL : 1 day.**"
    ),
    operation_id="list_map_gamemodes",
)
@validation_error_handler(response_model=GamemodeDetails)
async def list_map_gamemodes(request: Request) -> list[GamemodeDetails]:
    return await ListGamemodesRequestHandler(request).process_request()
