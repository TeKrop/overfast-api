"""Roles endpoints router : roles list, etc."""

from fastapi import APIRouter, BackgroundTasks, Request

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import RouteTag
from overfastapi.common.helpers import routes_responses
from overfastapi.handlers.list_roles_request_handler import ListRolesRequestHandler
from overfastapi.models.heroes import RoleDetail

router = APIRouter()


@router.get(
    "",
    response_model=list[RoleDetail],
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of roles",
    description="Get a list of available Overwatch roles.<br />**Cache TTL : 1 day.**",
)
@validation_error_handler(response_model=RoleDetail)
async def list_roles(background_tasks: BackgroundTasks, request: Request):
    return ListRolesRequestHandler(request).process_request(
        background_tasks=background_tasks
    )