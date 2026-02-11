"""Tests for Prometheus middleware"""

import pytest
from fastapi import FastAPI
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
        msg = "Test error"
        raise ValueError(msg)

    # Add middleware directly
    app.add_middleware(PrometheusMiddleware)  # type: ignore[arg-type]

    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


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
    with pytest.raises(ValueError, match="Test error"):
        client.get("/error")

    # Check metrics were recorded with 500 status
    metrics = REGISTRY.get_sample_value(
        "api_requests_total",
        {"method": "GET", "endpoint": "/error", "status": "500"},
    )
    assert metrics is not None
    assert metrics >= 1


def test_prometheus_middleware_skips_metrics_endpoint(test_app):
    """Test that middleware skips /metrics endpoint itself"""

    # Add a /metrics endpoint
    @test_app.get("/metrics")
    async def metrics_endpoint():
        return {"metrics": "data"}

    client = TestClient(test_app)

    # Make request to /metrics
    response = client.get("/metrics")
    expected_status_code = 200
    assert response.status_code == expected_status_code

    # Check that /metrics endpoint itself is not tracked
    metrics = REGISTRY.get_sample_value(
        "api_requests_total",
        {"method": "GET", "endpoint": "/metrics", "status": "200"},
    )
    # Should be None or very small (from other tests if run in parallel)
    # The point is it shouldn't increment for this specific call
    assert metrics is None or metrics < 1


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
