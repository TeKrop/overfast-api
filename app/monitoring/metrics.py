"""Prometheus metrics definitions for OverFast API

All metrics are defined here and imported throughout the application.
Metrics collection is conditional on settings.prometheus_enabled flag.
"""

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
