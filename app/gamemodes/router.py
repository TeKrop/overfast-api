"""Gamemodes endpoints router : gamemodes list, etc."""

from typing import Any

from fastapi import APIRouter, Request, Response

from app.enums import RouteTag
from app.helpers import success_responses

from .controllers.list_gamemodes_controller import ListGamemodesController
from .models import GamemodeDetails

router = APIRouter()


@router.get(
    "",
    responses=success_responses,
    tags=[RouteTag.GAMEMODES],
    summary="Get a list of gamemodes",
    description=(
        "Get a list of Overwatch gamemodes : Assault, Escort, Flashpoint, Hybrid, etc."
        f"<br />**Cache TTL : {ListGamemodesController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_map_gamemodes",
    response_model=list[GamemodeDetails],
)
async def list_map_gamemodes(request: Request, response: Response) -> Any:
    return await ListGamemodesController(request, response).process_request()
