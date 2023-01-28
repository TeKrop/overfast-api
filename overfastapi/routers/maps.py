"""Maps endpoints router : maps list, etc."""
from fastapi import APIRouter, BackgroundTasks, Query, Request

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import MapGamemode, RouteTag
from overfastapi.handlers.list_maps_request_handler import ListMapsRequestHandler
from overfastapi.models.maps import Map

router = APIRouter()


@router.get(
    "",
    tags=[RouteTag.MAPS],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps : Hanamura, King's Row, Dorado, etc."
        "<br />**Cache TTL : 1 day.**"
    ),
)
@validation_error_handler(response_model=Map)
async def list_maps(
    background_tasks: BackgroundTasks,
    request: Request,
    gamemode: MapGamemode
    | None = Query(
        None,
        title="Gamemode filter",
        description="Filter maps available for a specific gamemode",
    ),
) -> list[Map]:
    return ListMapsRequestHandler(request).process_request(
        background_tasks=background_tasks, gamemode=gamemode
    )
