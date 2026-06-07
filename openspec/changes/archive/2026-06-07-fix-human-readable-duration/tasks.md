## 1. Implementation

- [x] 1.1 Add `"less than a minute"` fallback to `get_human_readable_duration` in `app/api/helpers.py`

## 2. Tests

- [x] 2.1 Add parametrize case `(30, "less than a minute")` to `test_get_human_readable_duration` in `tests/infrastructure/test_helpers.py`

## 3. Verify

- [x] 3.1 Run `just check` — type checker passes
- [x] 3.2 Run `just lint` — no lint errors
- [x] 3.3 Run `just test tests/infrastructure/test_helpers.py` — all tests pass
