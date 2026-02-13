"""Prometheus middleware for FastAPI request tracking

Tracks request count, duration, status, and in-progress requests per endpoint.
Only active when settings.prometheus_enabled is True.
"""

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings
from app.monitoring.helpers import normalize_endpoint
from app.monitoring.metrics import (
    api_request_duration_seconds,
    api_requests_in_progress,
    api_requests_total,
)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request
    from starlette.responses import Response


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for API requests"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Track request count, duration, status per endpoint

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler

        Returns:
            HTTP response
        """
        # Skip if metrics are disabled (safety guard for future reuse)
        if not settings.prometheus_enabled:
            return await call_next(request)

        # Extract endpoint info
        method = request.method
        path = request.url.path

        # Skip metrics endpoint itself
        if path == "/metrics":
            return await call_next(request)

        # Normalize path to avoid high cardinality
        normalized_path = normalize_endpoint(path)

        # Track in-progress requests
        api_requests_in_progress.labels(method=method, endpoint=normalized_path).inc()

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            # Track failed requests
            api_requests_total.labels(
                method=method, endpoint=normalized_path, status="500"
            ).inc()
            raise
        finally:
            # Track request duration and decrement in-progress
            duration = time.perf_counter() - start_time
            api_request_duration_seconds.labels(
                method=method, endpoint=normalized_path
            ).observe(duration)
            api_requests_in_progress.labels(
                method=method, endpoint=normalized_path
            ).dec()

        # Track completed requests
        api_requests_total.labels(
            method=method, endpoint=normalized_path, status=str(status)
        ).inc()

        return response


def register_prometheus_middleware(app: FastAPI) -> None:
    """
    Register Prometheus middleware if enabled

    Args:
        app: FastAPI application instance
    """
    if not settings.prometheus_enabled:
        return

    app.add_middleware(PrometheusMiddleware)  # type: ignore[arg-type]
