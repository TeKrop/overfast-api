# Adaptive Rate Limiting System

## Overview

OverFast API now uses an **adaptive rate limiting system** for requests to Blizzard's API. This system:
- Queues and throttles requests proactively
- Adjusts rate limits dynamically based on Blizzard's responses  
- Provides comprehensive metrics for monitoring and tuning
- **Maintains backward-compatible error codes** (HTTP 429) for seamless migration

## Key Benefits

1. **No global user blocking** - Requests are queued individually, not blocked globally
2. **Self-adjusting** - System learns optimal rate automatically using AIMD algorithm
3. **Better resource utilization** - Proactive throttling prevents violations
4. **Full visibility** - Comprehensive metrics for monitoring and tuning
5. **Backward compatible** - Same error codes/messages as before

## Quick Start for Production (1M+ calls/day)

### 1. Configuration

Add to your `.env` file:

```bash
# Adaptive Rate Limiting
BLIZZARD_MAX_CONCURRENT_REQUESTS=20
BLIZZARD_INITIAL_RATE_LIMIT=5.0
BLIZZARD_MIN_RATE_LIMIT=2.0
BLIZZARD_MAX_RATE_LIMIT=30.0
BLIZZARD_RATE_DECREASE_FACTOR=0.4
BLIZZARD_RATE_INCREASE_STEP=0.25

# Monitoring (Required)
MONITORING_ENABLED=true
MONITORING_ADMIN_TOKEN=$(openssl rand -hex 32)
```

### 2. Start Monitoring

```bash
# Restart application
just down && just start

# Watch metrics (every 60 seconds)
watch -n 60 'curl -s -H "X-Admin-Token: YOUR_TOKEN" http://localhost:8000/monitoring/metrics | jq'
```

### 3. Expected Metrics (Healthy System)

For ~1M API calls/day (~3.5 req/s to Blizzard):

```json
{
  "active_requests": 2-5,
  "max_concurrent_requests": 12-16,
  "requests_per_second_last_60s": 3.5-5.0,
  "current_rate_limit": 8-15,
  "rate_limit_percentage": 0.01-0.1,
  "avg_response_time_ms": 200-400
}
```

## How It Works

### Request Flow

1. **Semaphore Queue**: Limits concurrent requests to Blizzard (default: 20)
2. **Rate Limiter**: Controls requests per second using AIMD algorithm
3. **Metrics Tracking**: Records every request for analysis

### AIMD Algorithm

**On Success (HTTP 200):**
```
current_rate = min(max_rate, current_rate + 0.25)
```

**On Rate Limit (HTTP 403):**
```
current_rate = max(min_rate, current_rate * 0.4)
```

This gradually finds the optimal rate without manual tuning.

## Configuration Parameters

| Parameter | Default | Production | Description |
|-----------|---------|------------|-------------|
| `BLIZZARD_MAX_CONCURRENT_REQUESTS` | 10 | 20 | Max simultaneous requests to Blizzard |
| `BLIZZARD_INITIAL_RATE_LIMIT` | 10.0 | 5.0 | Starting rate (req/s) |
| `BLIZZARD_MIN_RATE_LIMIT` | 1.0 | 2.0 | Floor rate (req/s) |
| `BLIZZARD_MAX_RATE_LIMIT` | 50.0 | 30.0 | Ceiling rate (req/s) |
| `BLIZZARD_RATE_DECREASE_FACTOR` | 0.5 | 0.4 | Backoff multiplier on 403 |
| `BLIZZARD_RATE_INCREASE_STEP` | 0.5 | 0.25 | Increase step on success |

## Tuning Guide

### Check Rate Limiting

**If `rate_limit_percentage` > 0.5%** (too aggressive):
```bash
BLIZZARD_MAX_RATE_LIMIT=20.0  # Lower ceiling
BLIZZARD_RATE_DECREASE_FACTOR=0.3  # More aggressive backoff
```

**If `rate_limit_percentage` < 0.05%** (too conservative):
```bash
BLIZZARD_MAX_RATE_LIMIT=40.0  # Raise ceiling
BLIZZARD_RATE_INCREASE_STEP=0.5  # Faster ramp-up
```

### Check Concurrent Requests

**If `max_concurrent_requests` ≥ 18** (near limit):
```bash
BLIZZARD_MAX_CONCURRENT_REQUESTS=30  # Increase for burst traffic
```

**If `max_concurrent_requests` ≤ 8** (underutilized):
```bash
BLIZZARD_MAX_CONCURRENT_REQUESTS=15  # Decrease to save resources
```

## Monitoring Endpoints

### Get Metrics
```bash
curl -H "X-Admin-Token: YOUR_TOKEN" http://localhost:8000/monitoring/metrics
```

### Reset Peak Metrics
```bash
curl -X POST -H "X-Admin-Token: YOUR_TOKEN" http://localhost:8000/monitoring/metrics/reset
```

## Backward Compatibility

### Error Behavior (Unchanged for Users)

When Blizzard rate limits (HTTP 403):
- **Status Code**: HTTP 429 (Too Many Requests) - **same as before**
- **Error Message**: "API has been rate limited by Blizzard, please wait for 5 seconds before retrying" - **same as before**
- **Header**: `Retry-After: 5` - **same as before**

**What Changed Internally:**
- Old: All users blocked globally for 5 seconds
- New: Each request handled individually with adaptive throttling
- Result: Users see same errors, but less frequently

### Migration Path

**Phase 1: Monitor (Current)**
- Deploy with backward-compatible errors
- Collect metrics for 1-2 weeks
- Tune configuration based on data
- **No user impact**

**Phase 2: Optimize (Future)**
- Once tuned, consider updating error messages
- Provide more helpful information to users
- Communicate changes in release notes

## Troubleshooting

### High `rate_limit_percentage` (> 1%)

**Symptom**: Getting rate limited too often

**Solution**:
1. Lower `BLIZZARD_MAX_RATE_LIMIT` by 30%
2. Increase `BLIZZARD_RATE_DECREASE_FACTOR` for faster backoff
3. Monitor for 24 hours and adjust

### High Response Times (> 1000ms)

**Symptom**: Requests queuing for too long

**Solution**:
1. Check `active_requests` - if near limit, increase `BLIZZARD_MAX_CONCURRENT_REQUESTS`
2. Check `current_rate_limit` - if at max, increase `BLIZZARD_MAX_RATE_LIMIT`
3. Review traffic patterns - may need capacity planning

### `current_rate_limit` Stuck at Minimum

**Symptom**: System can't ramp up rate

**Solution**:
1. Blizzard may have tightened limits
2. Lower `BLIZZARD_INITIAL_RATE_LIMIT` and `BLIZZARD_MAX_RATE_LIMIT`
3. Accept this as new baseline and monitor

## Traffic Patterns (1M calls/day)

### Expected Blizzard Load

| Endpoint | Cache Hit | Blizzard Load |
|----------|-----------|---------------|
| `/heroes`, `/maps` | 98% | Very Low |
| `/players/{id}/summary` | 70-80% | Medium |
| `/players/{id}` | 70-80% | Medium |
| `/players?name=X` | 50-60% | Higher |

### Peak Multipliers

- Normal: 1x (3.5 req/s)
- Evening/Weekend: 2-3x (7-10 req/s)
- Patch/Event: 4-5x (14-18 req/s)
- Season Reset: 5-10x (18-35 req/s)

## References

- [AIMD Algorithm](https://en.wikipedia.org/wiki/Additive_increase/multiplicative_decrease)
- [TCP Congestion Control](https://en.wikipedia.org/wiki/TCP_congestion_control)
