"""Documentation routes (Redoc and Swagger UI)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html

if TYPE_CHECKING:
    from fastapi.responses import HTMLResponse

from app.api.docs import _DOC_TITLE, _FAVICON_URL, _OPENAPI_URL, render_documentation

router = APIRouter()


@router.get("/", include_in_schema=False)
async def overridden_redoc() -> HTMLResponse:
    return render_documentation(
        title=_DOC_TITLE,
        favicon_url=_FAVICON_URL,
        openapi_url=_OPENAPI_URL,
    )


@router.get("/docs", include_in_schema=False)
async def overridden_swagger() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=_OPENAPI_URL,
        title=_DOC_TITLE,
        swagger_favicon_url=_FAVICON_URL,
    )
