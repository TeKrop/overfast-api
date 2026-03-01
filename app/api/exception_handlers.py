"""FastAPI exception handler registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.exceptions import ResponseValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.helpers import overfast_internal_error
from app.api.responses import ASCIIJSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI, Request


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the given FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException):
        return ASCIIJSONResponse(
            content={"error": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(ResponseValidationError)
    async def pydantic_validation_error_handler(
        request: Request, error: ResponseValidationError
    ):
        raise overfast_internal_error(request.url.path, error) from error
