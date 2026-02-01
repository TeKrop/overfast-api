"""Monitoring endpoints for tracking Blizzard API request metrics"""

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.overfast_client import OverFastClient

router = APIRouter()


@router.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Get Blizzard API request metrics",
    description=(
        "Get real-time metrics about requests made to Blizzard's API, including "
        "concurrent requests, rate limiting status, and performance statistics. "
        "This endpoint requires an admin token for access."
    ),
    response_model=dict[str, Any],
)
async def get_metrics(
    x_admin_token: Annotated[
        str | None, Header(description="Admin authentication token")
    ] = None,
) -> dict[str, Any]:
    """Get current Blizzard API metrics"""
    # Simple token-based authentication
    if (
        not settings.monitoring_admin_token
        or x_admin_token != settings.monitoring_admin_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )

    client = OverFastClient()
    return await client.get_metrics()


@router.post(
    "/metrics/reset",
    tags=["Monitoring"],
    summary="Reset peak metrics",
    description="Reset peak concurrent request metrics. Requires admin token.",
)
async def reset_metrics(
    x_admin_token: Annotated[
        str | None, Header(description="Admin authentication token")
    ] = None,
) -> dict[str, str]:
    """Reset peak metrics"""
    if (
        not settings.monitoring_admin_token
        or x_admin_token != settings.monitoring_admin_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )

    client = OverFastClient()
    await client.reset_metrics()
    return {"message": "Peak metrics reset successfully"}
