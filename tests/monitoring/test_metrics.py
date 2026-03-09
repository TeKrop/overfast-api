"""Tests for monitoring/metrics.py — track_storage_operation decorator and _record_metrics"""

import pytest
from prometheus_client import REGISTRY

from app.monitoring.metrics import (
    _record_metrics,
    track_storage_operation,
)


def _counter_value(name: str, **labels) -> float:
    """Read a prometheus counter value from the default registry."""
    try:
        return REGISTRY.get_sample_value(name + "_total", labels) or 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _histogram_count(name: str, **labels) -> float:
    """Read a prometheus histogram _count value from the default registry."""
    try:
        return REGISTRY.get_sample_value(name + "_count", labels) or 0.0
    except Exception:  # noqa: BLE001
        return 0.0


class TestTrackStorageOperationDecorator:
    """Tests for the track_storage_operation decorator."""

    @pytest.mark.asyncio
    async def test_async_function_success_records_metrics(self):
        """Decorated async function succeeds: returns value and status=success counter incremented."""

        @track_storage_operation("player_profiles", "get")
        async def _async_get():
            return "result"

        before = _counter_value(
            "storage_operations",
            table="player_profiles",
            operation="get",
            status="success",
        )

        result = await _async_get()

        assert result == "result"
        after = _counter_value(
            "storage_operations",
            table="player_profiles",
            operation="get",
            status="success",
        )
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_async_function_reraises_exception(self):
        """Decorated async function that raises: exception propagates and status=error counter incremented."""

        @track_storage_operation("player_profiles", "set")
        async def _async_fail():
            msg = "DB error"
            raise RuntimeError(msg)

        before = _counter_value(
            "storage_operations",
            table="player_profiles",
            operation="set",
            status="error",
        )

        with pytest.raises(RuntimeError, match="DB error"):
            await _async_fail()

        after = _counter_value(
            "storage_operations",
            table="player_profiles",
            operation="set",
            status="error",
        )
        assert after == before + 1

    def test_sync_function_success_records_metrics(self):
        """Decorated sync function succeeds: returns value and status=success counter incremented."""

        @track_storage_operation("static_data", "get")
        def _sync_get():
            return 42

        before = _counter_value(
            "storage_operations", table="static_data", operation="get", status="success"
        )

        actual = _sync_get()

        assert actual == 42  # noqa: PLR2004
        after = _counter_value(
            "storage_operations", table="static_data", operation="get", status="success"
        )
        assert after == before + 1

    def test_sync_function_reraises_exception(self):
        """Decorated sync function that raises: exception propagates and status=error counter incremented."""

        @track_storage_operation("static_data", "delete")
        def _sync_fail():
            msg = "sync error"
            raise ValueError(msg)

        before = _counter_value(
            "storage_operations",
            table="static_data",
            operation="delete",
            status="error",
        )

        with pytest.raises(ValueError, match="sync error"):
            _sync_fail()

        after = _counter_value(
            "storage_operations",
            table="static_data",
            operation="delete",
            status="error",
        )
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_async_preserves_function_name(self):
        """@wraps preserves original function name on async wrappers."""

        @track_storage_operation("player_profiles", "get")
        async def my_custom_get():
            return None

        assert my_custom_get.__name__ == "my_custom_get"

    def test_sync_preserves_function_name(self):
        """@wraps preserves original function name on sync wrappers."""

        @track_storage_operation("static_data", "get")
        def my_sync_op():
            return None

        assert my_sync_op.__name__ == "my_sync_op"

    @pytest.mark.asyncio
    async def test_async_passes_args_and_kwargs(self):
        """Args and kwargs are forwarded to the wrapped async function."""

        @track_storage_operation("player_profiles", "get")
        async def _get(player_id: str, *, include_stats: bool = False):
            return (player_id, include_stats)

        result = await _get("test-player", include_stats=True)

        assert result == ("test-player", True)

    def test_sync_passes_args_and_kwargs(self):
        """Args and kwargs are forwarded to the wrapped sync function."""

        @track_storage_operation("static_data", "set")
        def _set(key: str, value: int = 0):
            return (key, value)

        actual = _set("heroes", value=5)

        assert actual == ("heroes", 5)

    @pytest.mark.asyncio
    async def test_async_records_duration(self):
        """Duration histogram is observed for async operations."""

        @track_storage_operation("player_profiles", "get")
        async def _async_op():
            return None

        before = _histogram_count(
            "storage_operation_duration_seconds",
            table="player_profiles",
            operation="get",
        )

        await _async_op()

        after = _histogram_count(
            "storage_operation_duration_seconds",
            table="player_profiles",
            operation="get",
        )
        assert after == before + 1

    def test_sync_records_duration(self):
        """Duration histogram is observed for sync operations."""

        @track_storage_operation("static_data", "set")
        def _sync_op():
            return None

        before = _histogram_count(
            "storage_operation_duration_seconds",
            table="static_data",
            operation="set",
        )

        _sync_op()

        after = _histogram_count(
            "storage_operation_duration_seconds",
            table="static_data",
            operation="set",
        )
        assert after == before + 1


class TestRecordMetrics:
    """Tests for _record_metrics helper (slow query threshold logic)."""

    def test_fast_query_no_slow_query_counter(self):
        """A fast query (< 100ms) does not increment any slow-query counter."""
        before_100ms = _counter_value(
            "storage_slow_queries",
            table="player_profiles",
            operation="get",
            threshold="100ms",
        )
        before_1s = _counter_value(
            "storage_slow_queries",
            table="player_profiles",
            operation="get",
            threshold="1s",
        )

        _record_metrics("player_profiles", "get", 0.01, "success")

        assert (
            _counter_value(
                "storage_slow_queries",
                table="player_profiles",
                operation="get",
                threshold="100ms",
            )
            == before_100ms
        )
        assert (
            _counter_value(
                "storage_slow_queries",
                table="player_profiles",
                operation="get",
                threshold="1s",
            )
            == before_1s
        )

    def test_moderately_slow_query_100ms_threshold(self):
        """A query > 100ms but < 1s increments the '100ms' threshold counter only."""
        before_100ms = _counter_value(
            "storage_slow_queries",
            table="player_profiles",
            operation="get",
            threshold="100ms",
        )
        before_1s = _counter_value(
            "storage_slow_queries",
            table="player_profiles",
            operation="get",
            threshold="1s",
        )

        _record_metrics("player_profiles", "get", 0.5, "success")

        assert (
            _counter_value(
                "storage_slow_queries",
                table="player_profiles",
                operation="get",
                threshold="100ms",
            )
            == before_100ms + 1
        )
        assert (
            _counter_value(
                "storage_slow_queries",
                table="player_profiles",
                operation="get",
                threshold="1s",
            )
            == before_1s
        )

    def test_very_slow_query_1s_threshold(self):
        """A query > 1s increments the '1s' threshold counter only."""
        before_100ms = _counter_value(
            "storage_slow_queries",
            table="player_profiles",
            operation="get",
            threshold="100ms",
        )
        before_1s = _counter_value(
            "storage_slow_queries",
            table="player_profiles",
            operation="get",
            threshold="1s",
        )

        _record_metrics("player_profiles", "get", 2.0, "success")

        assert (
            _counter_value(
                "storage_slow_queries",
                table="player_profiles",
                operation="get",
                threshold="100ms",
            )
            == before_100ms
        )
        assert (
            _counter_value(
                "storage_slow_queries",
                table="player_profiles",
                operation="get",
                threshold="1s",
            )
            == before_1s + 1
        )

    def test_error_status_recorded(self):
        """Status='error' is passed through and increments the error counter."""
        before = _counter_value(
            "storage_operations", table="static_data", operation="set", status="error"
        )

        _record_metrics("static_data", "set", 0.05, "error")

        after = _counter_value(
            "storage_operations", table="static_data", operation="set", status="error"
        )
        assert after == before + 1

    def test_operations_total_always_incremented(self):
        """storage_operations_total is always incremented regardless of duration or status."""
        before = _counter_value(
            "storage_operations",
            table="player_profiles",
            operation="get",
            status="success",
        )

        _record_metrics("player_profiles", "get", 0.001, "success")

        after = _counter_value(
            "storage_operations",
            table="player_profiles",
            operation="get",
            status="success",
        )
        assert after == before + 1
