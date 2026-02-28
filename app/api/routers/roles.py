"""Roles endpoints router : roles list, etc."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response

from app.api.dependencies import RoleServiceDep
from app.api.enums import RouteTag
from app.api.models.roles import RoleDetail
from app.config import settings
from app.domain.enums import Locale
from app.helpers import (
    apply_swr_headers,
    build_cache_key,
    get_human_readable_duration,
    routes_responses,
)

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of roles",
    description=(
        "Get a list of available Overwatch roles."
        f"<br />**Cache TTL : {get_human_readable_duration(settings.heroes_path_cache_timeout)}.**"
    ),
    operation_id="list_roles",
    response_model=list[RoleDetail],
)
async def list_roles(
    request: Request,
    response: Response,
    service: RoleServiceDep,
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> Any:
    data, is_stale, age = await service.list_roles(
        locale=locale, cache_key=build_cache_key(request)
    )
    apply_swr_headers(
        response,
        settings.heroes_path_cache_timeout,
        is_stale,
        age,
        staleness_threshold=settings.roles_staleness_threshold,
    )
    return data
