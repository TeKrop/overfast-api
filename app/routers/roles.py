"""Roles endpoints router : roles list, etc."""

from fastapi import APIRouter, Query, Request

from app.common.decorators import validation_error_handler
from app.common.enums import Locale, RouteTag
from app.common.helpers import routes_responses
from app.handlers.list_roles_request_handler import ListRolesRequestHandler
from app.models.heroes import RoleDetail

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of roles",
    description="Get a list of available Overwatch roles.<br />**Cache TTL : 1 day.**",
    operation_id="list_roles",
)
@validation_error_handler(response_model=RoleDetail)
async def list_roles(
    request: Request,
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> list[RoleDetail]:
    return await ListRolesRequestHandler(request).process_request(locale=locale)
