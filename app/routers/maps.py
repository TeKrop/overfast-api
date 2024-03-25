"""Maps endpoints router : maps list, etc."""

from fastapi import APIRouter, Query, Request

from app.common.decorators import validation_error_handler
from app.common.enums import MapGamemode, RouteTag
from app.handlers.list_maps_request_handler import ListMapsRequestHandler
from app.models.maps import Map

router = APIRouter()


@router.get(
    "",
    tags=[RouteTag.MAPS],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps : Hanamura, King's Row, Dorado, etc."
        "<br />**Cache TTL : 1 day.**"
    ),
    operation_id="list_maps",
)
@validation_error_handler(response_model=Map)
async def list_maps(
    request: Request,
    gamemode: MapGamemode = Query(
        None,
        title="Gamemode filter",
        description="Filter maps available for a specific gamemode",
    ),
) -> list[Map]:
    return await ListMapsRequestHandler(request).process_request(gamemode=gamemode)
