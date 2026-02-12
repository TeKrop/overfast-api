"""Tests for Prometheus middleware"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app import config
from app.monitoring.middleware import (
    PrometheusMiddleware,
    register_prometheus_middleware,
)


@pytest.fixture
def test_app():
    """Create a test FastAPI app with Prometheus middleware"""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/error")
    async def error_endpoint():
        raise HTTPException(status_code=500, detail="Test error")

    @app.get("/players/{player_id}/summary")
    async def player_summary(player_id: str):
        return {"player_id": player_id}

    # Add middleware directly
    app.add_middleware(PrometheusMiddleware)  # type: ignore[arg-type]

    return app


@pytest.fixture
def client(test_app):
    """Create test client with prometheus enabled"""
    # Mock prometheus_enabled to be True for all middleware tests
    with patch.object(config.settings, "prometheus_enabled", True):
        yield TestClient(test_app)


def _get_in_progress_value(method: str, endpoint: str) -> float:
    """Helper to read in-progress gauge, treating missing as 0."""
    value = REGISTRY.get_sample_value(
        "api_requests_in_progress",
        {"method": method, "endpoint": endpoint},
    )
    return value or 0.0


def test_prometheus_middleware_tracks_successful_requests(client):
    """Test that middleware tracks successful requests"""
    # Make request
    response = client.get("/test")

    expected_status_code = 200
    assert response.status_code == expected_status_code

    # Check metrics were recorded
    metrics = REGISTRY.get_sample_value(
        "api_requests_total",
        {"method": "GET", "endpoint": "/test", "status": "200"},
    )
    assert metrics is not None
    assert metrics >= 1


def test_prometheus_middleware_tracks_request_duration(client):
    """Test that middleware tracks request duration"""
    # Make request
    response = client.get("/test")

    expected_status_code = 200
    assert response.status_code == expected_status_code

    # Check duration histogram was updated
    # The histogram creates multiple metrics (_count, _sum, _bucket)
    count_metric = REGISTRY.get_sample_value(
        "api_request_duration_seconds_count",
        {"method": "GET", "endpoint": "/test"},
    )
    assert count_metric is not None
    assert count_metric >= 1


def test_prometheus_middleware_tracks_failed_requests(client):
    """Test that middleware tracks failed requests"""
    # Make request that will fail
    response = client.get("/error")

    # Check response is 500
    expected_status_code = 500
    assert response.status_code == expected_status_code

    # Check metrics were recorded with 500 status
    metrics = REGISTRY.get_sample_value(
        "api_requests_total",
        {"method": "GET", "endpoint": "/error", "status": "500"},
    )
    assert metrics is not None
    assert metrics >= 1


def test_prometheus_middleware_normalizes_dynamic_paths(client):
    """Dynamic route metrics use normalized endpoint label"""
    # Hit a route with a path parameter
    response = client.get("/players/TeKrop-2217/summary")

    expected_status_code = 200
    assert response.status_code == expected_status_code

    # The middleware should normalize the endpoint label
    metrics = REGISTRY.get_sample_value(
        "api_requests_total",
        {
            "method": "GET",
            "endpoint": "/players/{player_id}/summary",
            "status": "200",
        },
    )
    assert metrics is not None
    assert metrics >= 1


def test_in_progress_gauge_resets_for_successful_request(client):
    """Gauge is incremented and then decremented for successful requests."""
    endpoint_label = "/test"
    method = "GET"

    before = _get_in_progress_value(method, endpoint_label)

    response = client.get(endpoint_label)
    expected_status_code = 200
    assert response.status_code == expected_status_code

    after = _get_in_progress_value(method, endpoint_label)

    # Gauge should return to original value after request completes
    assert after == before


def test_in_progress_gauge_resets_for_failing_request(client):
    """Gauge is incremented and then decremented even when the request fails."""
    endpoint_label = "/error"
    method = "GET"
    min_error_code = 400
    max_error_code = 600

    before = _get_in_progress_value(method, endpoint_label)

    response = client.get(endpoint_label)
    # Route is expected to return an error (4xx/5xx)
    assert min_error_code <= response.status_code < max_error_code

    after = _get_in_progress_value(method, endpoint_label)

    # Gauge should return to original value after request completes, even on error
    assert after == before


def test_prometheus_middleware_skips_metrics_endpoint(test_app):
    """Test that middleware skips /metrics endpoint itself"""

    # Add a /metrics endpoint
    @test_app.get("/metrics")
    async def metrics_endpoint():
        return {"metrics": "data"}

    client = TestClient(test_app)

    # Snapshot metric value before the request
    before = (
        REGISTRY.get_sample_value(
            "api_requests_total",
            {"method": "GET", "endpoint": "/metrics", "status": "200"},
        )
        or 0
    )

    # Make request to /metrics
    response = client.get("/metrics")
    expected_status_code = 200
    assert response.status_code == expected_status_code

    # Ensure the /metrics endpoint itself is not tracked
    after = (
        REGISTRY.get_sample_value(
            "api_requests_total",
            {"method": "GET", "endpoint": "/metrics", "status": "200"},
        )
        or 0
    )
    assert after == before


def test_register_prometheus_middleware_when_enabled(monkeypatch):
    """Test middleware registration when enabled"""
    monkeypatch.setattr(config.settings, "prometheus_enabled", True)

    app = FastAPI()
    initial_middleware_count = len(app.user_middleware)

    register_prometheus_middleware(app)

    # Middleware should be added
    assert len(app.user_middleware) == initial_middleware_count + 1


def test_register_prometheus_middleware_when_disabled(monkeypatch):
    """Test middleware registration when disabled"""
    monkeypatch.setattr(config.settings, "prometheus_enabled", False)

    app = FastAPI()
    initial_middleware_count = len(app.user_middleware)

    register_prometheus_middleware(app)

    # Middleware should NOT be added
    assert len(app.user_middleware) == initial_middleware_count
