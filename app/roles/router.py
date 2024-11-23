"""Roles endpoints router : roles list, etc."""

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.enums import Locale, RouteTag
from app.helpers import routes_responses

from .controllers.list_roles_controller import ListRolesController
from .models import RoleDetail

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of roles",
    description=(
        "Get a list of available Overwatch roles."
        f"<br />**Cache TTL : {ListRolesController.get_human_readable_timeout()}.**"
    ),
    operation_id="list_roles",
)
async def list_roles(
    request: Request,
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> list[RoleDetail]:
    return await ListRolesController(request).process_request(locale=locale)
