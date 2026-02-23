"""Gamemodes endpoints router : gamemodes list, etc."""

from typing import Any

from fastapi import APIRouter, Request, Response

from app.api.dependencies import GamemodeServiceDep
from app.config import settings
from app.enums import RouteTag
from app.gamemodes.models import GamemodeDetails
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
    tags=[RouteTag.GAMEMODES],
    summary="Get a list of gamemodes",
    description=(
        "Get a list of Overwatch gamemodes : Assault, Escort, Flashpoint, Hybrid, etc."
        f"<br />**Cache TTL : {get_human_readable_duration(settings.csv_cache_timeout)}.**"
    ),
    operation_id="list_map_gamemodes",
    response_model=list[GamemodeDetails],
)
async def list_map_gamemodes(
    request: Request,
    response: Response,
    service: GamemodeServiceDep,
) -> Any:
    data, is_stale, age = await service.list_gamemodes(
        cache_key=build_cache_key(request)
    )
    apply_swr_headers(
        response,
        settings.csv_cache_timeout,
        is_stale,
        age,
        staleness_threshold=settings.gamemodes_staleness_threshold,
    )
    return data
