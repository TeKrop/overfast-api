## Why

`get_human_readable_duration` returns an empty string for durations under 60 seconds, causing route description strings across all routers to render as `"Cache TTL : ."` — broken API documentation silently shipped to users.

## What Changes

- Add a `"less than a minute"` fallback when no time unit parts are produced
- Add a parametrized test case covering `duration < 60`

## Capabilities

### New Capabilities

### Modified Capabilities
- `human-readable-duration`: `get_human_readable_duration` now returns a non-empty string for all non-negative integer inputs, including sub-minute durations

## Impact

- `app/api/helpers.py`: Add fallback branch in `get_human_readable_duration`
- `tests/infrastructure/test_helpers.py`: Add one parametrize entry for `duration=30`
