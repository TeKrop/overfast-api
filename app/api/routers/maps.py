"""Maps endpoints router : maps list, etc."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response

from app.api.dependencies import MapServiceDep
from app.config import settings
from app.enums import RouteTag
from app.gamemodes.enums import MapGamemode
from app.helpers import apply_swr_headers, success_responses
from app.maps.models import Map

router = APIRouter()


@router.get(
    "",
    responses=success_responses,
    tags=[RouteTag.MAPS],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps : Hanamura, King's Row, Dorado, etc."
        f"<br />**Cache TTL : {settings.csv_cache_timeout} seconds.**"
    ),
    operation_id="list_maps",
    response_model=list[Map],
)
async def list_maps(
    request: Request,
    response: Response,
    service: MapServiceDep,
    gamemode: Annotated[
        MapGamemode | None,  # ty: ignore[invalid-type-form]
        Query(
            title="Gamemode filter",
            description="Filter maps available for a specific gamemode",
        ),
    ] = None,
) -> Any:
    cache_key = request.url.path + (
        f"?{request.query_params}" if request.query_params else ""
    )
    data, is_stale, age = await service.list_maps(
        gamemode=gamemode, cache_key=cache_key
    )
    apply_swr_headers(response, settings.csv_cache_timeout, is_stale, age)
    return data
