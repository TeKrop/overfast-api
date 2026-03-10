# AGENTS.md

Guidance for automated assistants and code agents when interacting with this repository.

---

## Project overview

OverFast API is a FastAPI-based Overwatch data API that scrapes Blizzard pages to provide data about heroes, game modes, maps, and player statistics. It uses a Stale-While-Revalidate (SWR) caching strategy backed by Valkey, with Nginx/OpenResty as a reverse proxy. The codebase follows Domain-Driven Design (DDD) with a strict layering policy. Python 3.14+, package manager is `uv`.

---

## Build, run, and test commands

All commands use `just` (or `make` as an alternative). Linting/type-checking run locally via `uv`; tests run inside Docker.

```bash
just build                                                       # Build Docker images (required first)
just start                                                       # Run app with autoreload on localhost:8000
just down                                                        # Stop all containers
just check                                                       # Run ty type checker (uv run ty check)
just lint                                                        # Run ruff linter with --fix
just format                                                      # Run ruff formatter
just test                                                        # Run all tests with coverage (-n auto, parallel)
just test tests/domain/services/                                 # Run a specific test directory
just test tests/adapters/blizzard/test_client.py                 # Run a specific test file
just test "tests/ -k test_get_hero_by_key"                       # Run tests matching a keyword
just shell                                                       # Interactive shell in container
just exec "command"                                              # Execute arbitrary command in container
```

CI enforces **80% minimum coverage**. Always run `just check`, `just lint`, and `just test` before proposing changes.

Pre-commit hooks (`ruff` lint + `ruff-format` + `ty` type checking) are configured in `.pre-commit-config.yaml`.

---

## Architecture summary

Four strict DDD layers; dependencies only flow inward.

| Layer | May depend on | Must not depend on |
|---|---|---|
| `domain` | stdlib, `infrastructure` (logger only) | `adapters`, `api` |
| `adapters` | `domain`, `infrastructure` | `api` |
| `api` | `domain`, `adapters` (via DI), `infrastructure` | — |
| `infrastructure` | anything | — |

```
app/
├── main.py                        # Thin app assembler
├── config.py                      # Pydantic BaseSettings (settings singleton)
├── domain/
│   ├── enums.py                   # All domain enums; HeroKey/MapKey built dynamically from CSV
│       ├── exceptions.py              # Domain exceptions (ParserParsingError, ParserInternalError, RateLimitedError, …)
│   ├── models/player.py           # PlayerIdentity, PlayerRequest dataclasses
│   ├── parsers/                   # HTML parsers (stateless functions, selectolax)
│   ├── ports/                     # typing.Protocol interfaces (structural typing)
│   ├── services/                  # SWR orchestration via get_or_fetch()
│   └── utils/
│       ├── csv_reader.py          # CSVReader class
│       └── data/                  # heroes.csv, maps.csv, gamemodes.csv
├── adapters/
│   ├── blizzard/
│   │   ├── client.py              # BlizzardClient (HTTP, throttle, metrics)
│   │   └── throttle.py            # BlizzardThrottle (TCP Slow Start + AIMD)
│   ├── cache/valkey_cache.py      # ValkeyCache (SWR envelope, zstd-compressed)
│   ├── storage/postgres_storage.py
│   └── tasks/
│       ├── valkey_broker.py       # ValkeyListBroker (taskiq)
│       ├── valkey_task_queue.py   # SWR enqueue, dedup via SET NX
│       ├── task_registry.py       # TASK_MAP — breaks circular import
│       └── worker.py              # taskiq tasks + cron jobs
├── api/
│   ├── dependencies.py            # FastAPI Depends() providers + type aliases
│   ├── exception_handlers.py
│       ├── helpers.py                 # SWR headers and response helpers (routes_responses, apply_swr_headers, …)
│   ├── lifespan.py
│   ├── responses.py               # ASCIIJSONResponse (default response class)
│   ├── models/                    # Pydantic response models
│   └── routers/
├── infrastructure/
│   ├── decorators.py              # @rate_limited
│   ├── helpers.py                 # overfast_internal_error, send_discord_webhook_message
│   ├── logger.py                  # loguru logger
│   └── metaclasses.py             # Singleton with clear_all()
└── monitoring/                    # Prometheus metrics + middleware
```

### Request flow

```
Router → get_* dependency (api/dependencies.py)
  → Service.get_or_fetch() (domain/services/)
    → CachePort.get()
      ├── HIT (fresh)  → return immediately
      ├── HIT (stale)  → return immediately + enqueue background refresh (TaskQueuePort)
      └── MISS         → BlizzardClientPort.fetch() → parse → CachePort.set() → return
```

---

## Code style

### Imports

1. `from __future__ import annotations` — only when needed (forward refs, circular import risk); not universal.
2. Standard library.
3. Third-party.
4. Local `app.*` imports.
5. `if TYPE_CHECKING:` block at the end for type-only imports (avoids runtime cost/circular imports).

`isort` is enforced by ruff (`I001`). `known-first-party = ["app"]`.

### Type hints

- Explicit type hints on **all** public function signatures (parameters and return types).
- Use `X | Y` union syntax (not `Union[X, Y]` or `Optional[X]`).
- Use `X | None = None` for optional fields/params (not `Optional[X]`).
- `Annotated[Type, ...]` used for FastAPI query/path params and for `Depends` aliases.
- `TYPE_CHECKING` guard for type-only imports to avoid runtime overhead.
- Protocol methods use `...` as body (not `pass`, not `raise NotImplementedError`).

### Naming

- `snake_case` — functions, variables, module attributes, config keys.
- `PascalCase` — all classes.
- `UPPER_SNAKE_CASE` — constants (e.g. `TASK_MAP`, `JOB_KEY_PREFIX`).
- `_leading_underscore` — private helpers and private Valkey key constants.
- CSV/static filenames and `key` column values — `lowercase-hyphenated`.

### Pydantic models

- All response models in `app/api/models/` inherit from `pydantic.BaseModel`.
- Every field uses `Field(...)` with `description=` and `examples=[...]`.
- Use `StrictInt`/`StrictFloat` where coercion must be prevented.
- Validators via `Field(ge=..., le=..., min_length=..., max_length=...)`.
- `HttpUrl`/`AnyHttpUrl` for URL fields.

### Error handling

- Domain exceptions (`ParserBlizzardError`, `ParserParsingError`, `RateLimitedError`, etc.) inherit from `OverfastError`.
- Assign `msg = "literal string"` before `raise` to satisfy ruff `EM` rule — no inline string literals in `raise`.
- Use `raise SomeException(msg) from exc` for exception chaining.
- Infrastructure errors (Valkey, DB) are caught with `except Exception:  # noqa: BLE001` and logged as warnings — never let them crash a request.
- `logger.critical(...)` + `overfast_internal_error(url, exc)` for unexpected parsing failures (sends Discord webhook, returns HTTP 500).

### Logging

- Use `from app.infrastructure.logger import logger` (loguru).
- Log levels: `debug`, `info`, `warning`, `error`, `critical` — `critical` is reserved for unexpected parsing failures.
- Always use loguru's native **brace-style** formatting: `logger.info("fetching {}", url)`.
  - Never use `%s`/`%d`/`%r` percent-style (stdlib `logging` style) — loguru ignores it silently instead of interpolating.
  - Never use f-strings in log calls — they are eagerly evaluated even when the log level is suppressed, defeating lazy evaluation.
  - Use `{!r}` for repr formatting: `logger.warning("unexpected value: {!r}", val)`.
  - Use format specs for floats: `logger.debug("took {:.3f}s", duration)`.

### Structural typing (Ports)

- All port interfaces in `app/domain/ports/` are `typing.Protocol` classes.
- Adapters do **not** inherit from ports — compliance is verified by `ty` at injection points.
- Port protocol methods have `...` as body.

### Singleton adapters

- `BlizzardClient`, `ValkeyCache`, `PostgresStorage`, `BlizzardThrottle` use `metaclass=Singleton`.
- Tests call `Singleton.clear_all()` (via autouse fixture) to reset between runs.

---

## Testing

- pytest with `fakeredis.FakeAsyncRedis` in-memory Valkey and a `FakeStorage` in-memory DB.
- `tests/conftest.py` autouse fixture: clears storage, calls `Singleton.clear_all()`, patches Valkey, overrides `get_storage` DI, disables Discord webhook + profiler.
- Test structure mirrors `app/` DDD layout (`tests/domain/`, `tests/adapters/`, etc.).
- HTML/JSON fixtures for parser tests: `tests/fixtures/`.
- Refresh test fixtures from live pages: `just exec "python -m tests.update_test_fixtures"`.
- `patch("httpx.AsyncClient.get", ...)` is the standard mock pattern for HTTP calls.
- `pytest.mark.parametrize` used extensively for enum coverage.
- Tests run in parallel via `pytest-xdist` (`-n auto`). Ensure test isolation.

### AAA pattern

All test methods must follow the **Arrange / Act / Assert** pattern, using blank lines (no comment labels) to separate the three sections:

```python
def test_something(self):
    input_data = build_input()

    result = call_under_test(input_data)

    assert result == expected
```

Rules:
- **Arrange** — setup and input construction.
- **Act** — the single call being tested, assigned to a variable (`result = ...`). Never inline inside `assert`.
- **Assert** — one or more `assert` statements.
- Each section separated by exactly one blank line.
- Never combine Act and Assert: `assert func(x) == y` must become `result = func(x)` + blank line + `assert result == y`.
- When using `with patch(...):`, the `response = client.get(...)` (Act) must be the last line inside the `with` block; all `assert` statements go after the block closes, separated by a blank line.

---

## Configuration

- `app/config.py` — `Settings(BaseSettings)`, accessed as `from app.config import settings`.
- Defaults documented in `.env.dist` — update it when adding new config flags.
- All setting names are `snake_case`; env var names are the `UPPER_CASE` equivalent.
- `@property` for computed settings (e.g. `postgres_dsn`).

---

## Data files and static assets

- Static data CSVs: `app/domain/utils/data/heroes.csv`, `maps.csv`, `gamemodes.csv`.
- Map screenshots: `static/maps/<key>.jpg`.
- `HeroKey`, `MapKey`, `MapGamemode` enums are **generated dynamically from CSVs** at import time — adding a new entry only requires updating the CSV.
- CSV `key` column values and filenames must use `lowercase-hyphenated` format.

---

## Commits and PRs

Conventional Commits are enforced by semantic-release:
- `feat:`, `fix:`, `build(deps):`, `chore:`, `docs:`
- Scoped: `feat(players):`, `fix(maps):`

Do not create branches, commits, or PRs unless explicitly asked. Include motivation and testing steps in PR descriptions. Call out breaking changes explicitly.

---

## Safety guidelines

- Never access secrets, API keys, or tokens; never add them to code or commits.
- Reproduce issues with `just test` or request CI logs before proposing fixes.
- Run `just check`, `just lint`, and `just test` before suggesting code to merge.
- Ask the maintainer before any action requiring env-specific values (branch names, secrets, remotes).
- For design changes affecting public API behavior or backwards compatibility, involve humans.
