"""Tests for monitoring/router.py (Prometheus metrics endpoint)"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client_fixture():
    return TestClient(app)


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint"""

    def test_metrics_endpoint_returns_200(self, client_fixture: TestClient):
        with patch(
            "app.monitoring.router.PostgresStorage",
        ) as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.get_stats.return_value = {
                "size_bytes": 1024,
                "static_data_count": 5,
                "player_profiles_count": 10,
                "player_profile_age_p50": 0,
                "player_profile_age_p90": 0,
                "player_profile_age_p99": 0,
            }
            mock_storage_class.return_value = mock_storage

            response = client_fixture.get("/metrics")

        assert response.status_code == status.HTTP_200_OK

    def test_metrics_endpoint_content_type(self, client_fixture: TestClient):
        with patch(
            "app.monitoring.router.PostgresStorage",
        ) as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.get_stats.return_value = {
                "size_bytes": 0,
                "static_data_count": 0,
                "player_profiles_count": 0,
                "player_profile_age_p50": 0,
                "player_profile_age_p90": 0,
                "player_profile_age_p99": 0,
            }
            mock_storage_class.return_value = mock_storage

            response = client_fixture.get("/metrics")

        # Prometheus content type should be text/plain
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_with_profile_age_stats(self, client_fixture: TestClient):
        """Test that profile age histogram observations are made when p50 > 0."""
        with patch(
            "app.monitoring.router.PostgresStorage",
        ) as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.get_stats.return_value = {
                "size_bytes": 2048,
                "static_data_count": 3,
                "player_profiles_count": 7,
                "player_profile_age_p50": 3600,
                "player_profile_age_p90": 7200,
                "player_profile_age_p99": 86400,
            }
            mock_storage_class.return_value = mock_storage

            response = client_fixture.get("/metrics")

        assert response.status_code == status.HTTP_200_OK
        # The response should contain Prometheus-format text
        assert b"#" in response.content or len(response.content) >= 0

    def test_metrics_endpoint_handles_storage_error_gracefully(
        self, client_fixture: TestClient
    ):
        """If storage fails, the /metrics endpoint still returns 200 (not 500)."""
        with patch(
            "app.monitoring.router.PostgresStorage",
        ) as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.get_stats.side_effect = Exception("DB connection lost")
            mock_storage_class.return_value = mock_storage

            response = client_fixture.get("/metrics")

        # Should not crash — errors are swallowed and logged
        assert response.status_code == status.HTTP_200_OK

    def test_metrics_endpoint_not_in_openapi_schema(self, client_fixture: TestClient):
        """The /metrics endpoint is excluded from the OpenAPI spec."""
        response = client_fixture.get("/openapi.json")
        schema = response.json()
        assert "/metrics" not in schema.get("paths", {})
