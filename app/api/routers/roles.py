"""Roles endpoints router : roles list, etc."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response

from app.enums import Locale, RouteTag
from app.helpers import routes_responses
from app.roles.controllers.list_roles_controller import ListRolesController
from app.roles.models import RoleDetail

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
    response_model=list[RoleDetail],
)
async def list_roles(
    request: Request,
    response: Response,
    locale: Annotated[
        Locale, Query(title="Locale to be displayed")
    ] = Locale.ENGLISH_US,
) -> Any:
    return await ListRolesController(request, response).process_request(locale=locale)
