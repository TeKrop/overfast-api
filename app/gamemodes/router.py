"""Gamemodes endpoints router : gamemodes list, etc."""

from fastapi import APIRouter, Request

from app.enums import RouteTag

from .controllers.list_gamemodes_controller import ListGamemodesController
from .models import GamemodeDetails

router = APIRouter()


@router.get(
    "",
    tags=[RouteTag.GAMEMODES],
    summary="Get a list of gamemodes",
    description=(
        "Get a list of Overwatch gamemodes : Assault, Escort, Flashpoint, Hybrid, etc."
        f"<br />**Cache TTL : {ListGamemodesController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_map_gamemodes",
)
async def list_map_gamemodes(request: Request) -> list[GamemodeDetails]:
    return await ListGamemodesController(request).process_request()
