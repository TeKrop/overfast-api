"""Maps endpoints router : maps list, etc."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response

from app.api.dependencies import MapServiceDep
from app.api.enums import RouteTag
from app.api.models.maps import Map
from app.config import settings
from app.domain.enums import MapGamemode
from app.helpers import (
    apply_swr_headers,
    build_cache_key,
    get_human_readable_duration,
    success_responses,
)

router = APIRouter()


@router.get(
    "",
    responses=success_responses,
    tags=[RouteTag.MAPS],
    summary="Get a list of maps",
    description=(
        "Get a list of Overwatch maps : Hanamura, King's Row, Dorado, etc."
        f"<br />**Cache TTL : {get_human_readable_duration(settings.csv_cache_timeout)}.**"
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
    data, is_stale, age = await service.list_maps(
        gamemode=gamemode, cache_key=build_cache_key(request)
    )
    apply_swr_headers(
        response,
        settings.csv_cache_timeout,
        is_stale,
        age,
        staleness_threshold=settings.maps_staleness_threshold,
    )
    return data
