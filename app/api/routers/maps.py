"""Maps endpoints router : maps list, etc."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response

from app.enums import RouteTag
from app.gamemodes.enums import MapGamemode
from app.helpers import success_responses
from app.maps.controllers.list_maps_controller import ListMapsController
from app.maps.models import Map

router = APIRouter()


@router.get(
    "",
    responses=success_responses,
    tags=[RouteTag.MAPS],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps : Hanamura, King's Row, Dorado, etc."
        f"<br />**Cache TTL : {ListMapsController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_maps",
    response_model=list[Map],
)
async def list_maps(
    request: Request,
    response: Response,
    gamemode: Annotated[
        MapGamemode | None,  # ty: ignore[invalid-type-form]
        Query(
            title="Gamemode filter",
            description="Filter maps available for a specific gamemode",
        ),
    ] = None,
) -> Any:
    return await ListMapsController(request, response).process_request(
        gamemode=gamemode
    )
