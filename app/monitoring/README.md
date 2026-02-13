# Monitoring Module

This module provides Prometheus metrics collection and monitoring for OverFast API.

## Architecture

- **metrics.py**: Centralized Prometheus metric definitions (counters, gauges, histograms)
- **middleware.py**: FastAPI middleware for tracking requests that reach the app (cache misses)
- **helpers.py**: Utility functions for metrics (endpoint normalization, URL normalization)

## Endpoint Normalization

### Why Normalization?

Without normalization, each unique player ID or hero key creates a separate metric label, leading to **metric cardinality explosion**. For example:
- `/players/TeKrop-2217/summary`
- `/players/Player-1234/summary`
- `/players/User-5678/summary`

Would create 3 separate metrics instead of 1. Prometheus performance degrades with high cardinality.

### Dual Implementation

Endpoint normalization is implemented in **two places**:

1. **Python** (`app/monitoring/helpers.py`): Used by FastAPI middleware for requests that reach the app
2. **Lua** (`build/nginx/prometheus_log.conf`): Used by Nginx for ALL requests (including cache hits)

### Keeping Them in Sync

**IMPORTANT**: When modifying normalization logic, update BOTH implementations to avoid divergence.

#### Normalization Rules

Both implementations must follow these exact patterns:

| Pattern | Raw Path | Normalized Path |
|---------|----------|----------------|
| Player with trailing segments | `/players/TeKrop-2217/summary` | `/players/{player_id}/summary` |
| Player without trailing segments | `/players/TeKrop-2217` | `/players/{player_id}` |
| Hero key (single segment, not "stats") | `/heroes/ana` | `/heroes/{hero_key}` |
| Hero stats | `/heroes/stats` | `/heroes/stats` (unchanged) |
| Heroes list | `/heroes` | `/heroes` (unchanged) |
| All other paths | `/maps`, `/gamemodes`, etc. | Unchanged |

#### Verification

When changing normalization logic:

1. **Update Python** (`app/monitoring/helpers.py` - `normalize_endpoint()`)
2. **Update Lua** (`build/nginx/prometheus_log.conf` - `normalize_endpoint()` function)
3. **Update tests** (`tests/monitoring/test_helpers.py` - `TestNormalizeEndpoint`)
4. **Run tests** to verify Python implementation
5. **Manual testing** to verify Nginx/Lua implementation:
   ```bash
   just up monitoring=true
   curl http://localhost:8080/players/TestPlayer-1234/summary
   curl http://localhost:9090/api/v1/query?query=nginx_http_requests_total
   # Verify label shows: endpoint="/players/{player_id}/summary"
   ```

#### Test Coverage

Tests in `tests/monitoring/test_helpers.py` cover:
- Player paths with and without trailing segments
- Hero paths (single segment vs `/heroes/stats`)
- Edge cases (trailing slashes, multiple segments)
- Different player ID formats (BattleTag, Blizzard ID)

These tests validate the **Python implementation only**. The Lua implementation must be manually verified or tested through integration tests.

## Blizzard URL Normalization

Separate from endpoint normalization, `normalize_blizzard_url()` in `helpers.py` normalizes Blizzard API URLs for tracking in `blizzard_requests_total` metrics. This prevents cardinality explosion from locale variations and dynamic IDs.

See function docstring and `TestNormalizeBlizzardUrl` tests for details.

## Usage

### Enabling Monitoring

Set `PROMETHEUS_ENABLED=true` in `.env`:
```bash
PROMETHEUS_ENABLED=true
```

### Starting with Monitoring Stack

```bash
# Start API + Prometheus + Grafana
just up monitoring=true

# Start API + Prometheus only
just up prometheus=true

# Start API + Grafana only
just up grafana=true
```

### Accessing Metrics

- FastAPI metrics: `http://localhost:8080/metrics` (Docker network only, blocked from public)
- Nginx metrics: `http://localhost:9145/metrics` (Docker network only)
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (default admin/admin or `GRAFANA_ADMIN_PASSWORD`)

### Dashboard Overview

Grafana dashboards are auto-provisioned from `build/grafana/provisioning/dashboards/`:
- **API Usage**: Request rates, cache hit rates, endpoint popularity
- **API Health**: Error rates, response times, status code distribution
- **Blizzard Calls**: Upstream request tracking, rate limiting
- **Tasks & Rate Limiting**: Background task metrics, AIMD congestion control
- **System Metrics**: Nginx connections, in-progress requests

## Performance

When `PROMETHEUS_ENABLED=false` (default):
- **Zero overhead**: No metrics collection, no middleware registration
- Nginx Lua blocks are empty (template substitution)
- FastAPI `/metrics` endpoint not registered

When `PROMETHEUS_ENABLED=true`:
- **Minimal overhead**: ~5-10μs per request for Nginx, ~10-50μs for FastAPI
- Shared memory zone (10MB) for Lua metrics
- In-memory Python counters with minimal locking
- At 10 rps: <0.1% CPU, <1ms additional latency

## Troubleshooting

### Metrics not appearing

1. Check `PROMETHEUS_ENABLED=true` in `.env`
2. Restart containers: `just down && just up monitoring=true`
3. Check Prometheus targets: `http://localhost:9090/targets`
4. Check logs: `docker compose logs prometheus`

### High cardinality warnings

If you see warnings about high cardinality labels:
1. Review endpoint normalization patterns
2. Check for new dynamic URL segments not being normalized
3. Update both Python and Lua implementations

### Lua errors in Nginx

Check Nginx error log:
```bash
docker compose logs nginx | grep error
```

Common issues:
- `prometheus` variable nil: `PROMETHEUS_ENABLED` not set or template substitution failed
- Pattern mismatch: Lua regex syntax differs from Python regex

## Further Reading

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [nginx-lua-prometheus](https://github.com/knyar/nginx-lua-prometheus)
- [RFC 5861: HTTP Cache-Control Extensions for Stale Content](https://tools.ietf.org/html/rfc5861)
