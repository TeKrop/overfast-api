"""Prometheus metrics definitions for OverFast API

All metrics are defined here and imported throughout the application.
Metrics collection is conditional on settings.prometheus_enabled flag.
"""

import inspect
import time
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram

##############
# API Metrics
##############

# Requests that reach FastAPI (Valkey cache misses)
api_requests_total = Counter(
    "api_requests_total",
    "Total HTTP requests reaching FastAPI (cache misses)",
    ["method", "endpoint", "status"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "Request duration at FastAPI level in seconds",
    ["method", "endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

api_requests_in_progress = Gauge(
    "api_requests_in_progress",
    "Number of requests currently being processed",
    ["method", "endpoint"],
)

####################
# Cache & SWR Metrics
####################

# Persistent storage lookups (Phase 3)
storage_hits_total = Counter(
    "storage_hits_total",
    "Persistent storage lookup results",
    ["result"],  # "hit", "miss"
)

# Stale responses served from persistent storage (Phase 3)
stale_responses_total = Counter(
    "stale_responses_total",
    "Stale responses served from persistent storage (SWR)",
)

# Background refresh tasks triggered (Phase 4 onwards)
background_refresh_triggered_total = Counter(
    "background_refresh_triggered_total",
    "Background refresh tasks triggered by SWR staleness detection",
    ["entity_type"],  # "heroes", "maps", "gamemodes", "roles", "player", "hero_stats"
)

########################
# Background Task Metrics (Phase 5)
########################

background_tasks_total = Counter(
    "background_tasks_total",
    "Background refresh tasks",
    [
        "task_type",
        "status",
    ],  # task_type: "player", "hero", etc. | status: "success", "failure"
)

background_tasks_queue_size = Gauge(
    "background_tasks_queue_size",
    "Current number of tasks waiting in queue",
    ["task_type"],
)

background_tasks_duration_seconds = Histogram(
    "background_tasks_duration_seconds",
    "Background task execution duration in seconds",
    ["task_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

########################
# AIMD / Blizzard Metrics (Phase 5)
########################

aimd_current_rate = Gauge(
    "aimd_current_rate",
    "Current allowed Blizzard request rate (requests per second)",
)

blizzard_requests_total = Counter(
    "blizzard_requests_total",
    "Total HTTP requests to Blizzard",
    ["endpoint", "status"],
)

blizzard_request_duration_seconds = Histogram(
    "blizzard_request_duration_seconds",
    "Blizzard request duration in seconds",
    ["endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

blizzard_rate_limited_total = Counter(
    "blizzard_rate_limited_total",
    "Times rate-limited by Blizzard (HTTP 403)",
)

########################
# Storage Metrics (Phase 3)
########################

storage_size_bytes = Gauge(
    "storage_size_bytes",
    "SQLite database file size in bytes",
)

storage_entries_total = Gauge(
    "storage_entries_total",
    "Total entries in persistent storage",
    ["table"],  # "player_profiles", "player_status", etc.
)

storage_write_errors_total = Counter(
    "storage_write_errors_total",
    "Failed writes to persistent storage",
    ["error_type"],  # "disk_error", "compression_error", "unknown"
)

# Phase 3.5B: Comprehensive SQLite monitoring
sqlite_operation_duration_seconds = Histogram(
    "sqlite_operation_duration_seconds",
    "SQLite operation duration in seconds",
    ["table", "operation"],  # operation: "get", "set", "delete"
    buckets=(
        0.0001,
        0.0005,
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    ),
)

sqlite_operations_total = Counter(
    "sqlite_operations_total",
    "Total SQLite operations",
    ["table", "operation", "status"],  # status: "success", "error"
)

sqlite_slow_queries_total = Counter(
    "sqlite_slow_queries_total",
    "SQLite queries exceeding threshold",
    ["table", "operation", "threshold"],  # threshold: "100ms", "1s"
)

sqlite_wal_size_bytes = Gauge(
    "sqlite_wal_size_bytes",
    "SQLite Write-Ahead Log file size in bytes",
)

# Cache effectiveness metrics
sqlite_cache_hit_total = Counter(
    "sqlite_cache_hit_total",
    "SQLite cache lookups by result",
    ["table", "result"],  # result: "hit", "miss"
)

sqlite_battletag_lookup_total = Counter(
    "sqlite_battletag_lookup_total",
    "BattleTag→Blizzard ID lookup optimization",
    ["result"],  # result: "hit", "miss"
)


# Data freshness metrics
sqlite_player_profile_age_seconds = Histogram(
    "sqlite_player_profile_age_seconds",
    "Age of player profiles in cache (seconds since last update)",
    buckets=(
        60,
        300,
        600,
        1800,
        3600,
        7200,
        21600,
        43200,
        86400,
        259200,
    ),  # 1min to 3 days
)

# Health metrics
sqlite_connection_errors_total = Counter(
    "sqlite_connection_errors_total",
    "SQLite connection errors",
    ["error_type"],
)

sqlite_lock_wait_duration_seconds = Histogram(
    "sqlite_lock_wait_duration_seconds",
    "Time spent waiting for SQLite locks",
    ["table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


##############
# SQLite Operation Tracking Decorator
##############

# Slow query thresholds (seconds)
SLOW_QUERY_THRESHOLD_1S = 1.0
SLOW_QUERY_THRESHOLD_100MS = 0.1

# Lock wait threshold (seconds) - operations taking >50ms might indicate lock contention
# SQLite with WAL mode has minimal lock contention, but this catches anomalies
LOCK_WAIT_THRESHOLD = 0.05


def _record_metrics(table: str, operation: str, duration: float, status: str):
    """Helper to record SQLite metrics (extracted to reduce complexity)"""
    sqlite_operation_duration_seconds.labels(table=table, operation=operation).observe(
        duration
    )
    sqlite_operations_total.labels(
        table=table, operation=operation, status=status
    ).inc()

    if duration > SLOW_QUERY_THRESHOLD_1S:
        sqlite_slow_queries_total.labels(
            table=table, operation=operation, threshold="1s"
        ).inc()
    elif duration > SLOW_QUERY_THRESHOLD_100MS:
        sqlite_slow_queries_total.labels(
            table=table, operation=operation, threshold="100ms"
        ).inc()

    # Track potential lock waits
    if operation in ("set", "delete", "update") and duration > LOCK_WAIT_THRESHOLD:
        sqlite_lock_wait_duration_seconds.labels(table=table).observe(duration)


def track_sqlite_operation(table: str, operation: str):
    """
    Decorator to automatically track SQLite operation metrics.

    Tracks duration, success/error counts, and slow queries for SQLite operations.
    All metrics are imported from this module (no circular dependencies).

    Args:
        table: Table name (e.g., "player_profiles", "static_data", "player_status")
        operation: Operation type (e.g., "get", "set", "delete")

    Usage:
        @track_sqlite_operation("player_profiles", "get")
        async def get_player_profile(self, player_id: str):
            ...

    Metrics tracked:
        - sqlite_operation_duration_seconds{table, operation}
        - sqlite_operations_total{table, operation, status}
        - sqlite_slow_queries_total{table, operation, threshold}
    """

    def decorator(func):
        # Support both async and sync functions
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    return await func(*args, **kwargs)
                except Exception:
                    status = "error"
                    raise
                finally:
                    _record_metrics(table, operation, time.time() - start_time, status)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                return func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                _record_metrics(table, operation, time.time() - start_time, status)

        return sync_wrapper

    return decorator
