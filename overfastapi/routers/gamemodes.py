# pylint: disable=R0913,C0116
"""Gamemodes endpoints router : gamemodes list, etc."""
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import ValidationError

from overfastapi.common.helpers import overfast_internal_error, routes_responses
from overfastapi.handlers.list_gamemodes_request_handler import (
    ListGamemodesRequestHandler,
)
from overfastapi.models.gamemodes import GamemodeDetails

router = APIRouter()


@router.get(
    "",
    response_model=list[GamemodeDetails],
    responses=routes_responses,
    tags=["Maps"],
    summary="Get a list of gamemodes",
    description="Get a list of Overwatch gamemodes : Assault, Escort, Hybrid, etc.",
)
async def list_map_gamemodes(
    background_tasks: BackgroundTasks,
    request: Request,
):
    gamemodes = ListGamemodesRequestHandler(request).process_request(
        background_tasks=background_tasks
    )
    try:
        return [GamemodeDetails(**gamemode) for gamemode in gamemodes]
    except ValidationError as error:
        raise overfast_internal_error(request.url.path, error) from error
