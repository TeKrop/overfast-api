from fastapi import APIRouter, BackgroundTasks, Request

from overfastapi.common.helpers import routes_responses, value_with_validation_check
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
    return value_with_validation_check(
        [GamemodeDetails(**gamemode) for gamemode in gamemodes]
    )
