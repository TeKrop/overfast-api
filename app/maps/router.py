"""Maps endpoints router : maps list, etc."""

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.enums import RouteTag
from app.gamemodes.enums import MapGamemode

from .controllers.list_maps_controller import ListMapsController
from .models import Map

router = APIRouter()


@router.get(
    "",
    tags=[RouteTag.MAPS],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps : Hanamura, King's Row, Dorado, etc."
        f"<br />**Cache TTL : {ListMapsController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_maps",
)
async def list_maps(
    request: Request,
    gamemode: Annotated[
        MapGamemode | None,
        Query(
            title="Gamemode filter",
            description="Filter maps available for a specific gamemode",
        ),
    ] = None,
) -> list[Map]:
    return await ListMapsController(request).process_request(gamemode=gamemode)
