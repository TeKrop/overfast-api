# AGENTS.md

Guidance for automated assistants and code agents (Copilot, Claude, ChatGPT, bots, or any automated code-review/run agents) when interacting with this repository.

This document is intended to be a concise, repository-specific checklist and reference so agents can work safely and productively with the codebase.

---

## Project overview

OverFast API is a FastAPI-based Overwatch data API that scrapes Blizzard pages to provide data about heroes, game modes, maps, and player statistics. It uses a Stale-While-Revalidate (SWR) caching strategy backed by Valkey, with Nginx/OpenResty as a reverse proxy. The codebase follows Domain-Driven Design (DDD) with a strict layering policy.

---

## Primary workflows (build, run, test)

Use the provided convenience commands (via just). Alternatives using make are supported.

Common commands:
```bash
just build              # Build Docker images (required first)
just start              # Run app with autoreload on localhost:8000
just start_testing      # Run with nginx reverse proxy on localhost:8080
just down               # Stop all containers
just check              # Run ty type checker
just lint               # Run ruff linter with --fix
just format             # Run ruff formatter
just test               # Run all tests with coverage
just test tests/domain  # Run a specific test directory
just test tests/adapters/blizzard/test_client.py  # Run a specific test file
just shell              # Interactive shell in container
just exec "command"     # Execute command in container
```

Make alternatives available: `make build`, `make start`, `make test PYTEST_ARGS="tests/domain"`, etc.

If you need to run anything that modifies the repo (commits, pushes, PRs), explicitly ask the human maintainer for permission, branch name, and commit message.

---

## Architecture summary

The project uses **Domain-Driven Design** with four strict layers. Dependencies only flow inward: `api` and `adapters` depend on `domain`; `domain` has no external dependencies.

```
app/
├── main.py                          # Thin app assembler
├── config.py                        # Pydantic BaseSettings
├── domain/                          # Pure domain — no external deps
│   ├── enums.py                     # All domain enums (Locale, Role, HeroKey, MapKey, etc.)
│   ├── exceptions.py                # Domain exceptions (ParserParsingError, RateLimitedError, etc.)
│   ├── models/
│   │   └── player.py                # PlayerIdentity, PlayerRequest dataclasses
│   ├── ports/                       # Protocols (structural typing — no explicit inheritance needed)
│   │   ├── blizzard_client.py       # BlizzardClientPort
│   │   ├── cache.py                 # CachePort
│   │   ├── storage.py               # StoragePort
│   │   ├── task_queue.py            # TaskQueuePort
│   │   └── throttle.py              # ThrottlePort
│   └── services/                    # Business logic (SWR orchestration via get_or_fetch)
│       ├── base_service.py          # BaseService
│       ├── hero_service.py
│       ├── role_service.py
│       ├── map_service.py
│       ├── gamemode_service.py
│       ├── player_service.py
│       └── static_data_service.py
├── adapters/                        # Port implementations (infrastructure)
│   ├── blizzard/
│   │   ├── client.py                # BlizzardClient (HTTP, throttle, metrics)
│   │   ├── throttle.py              # BlizzardThrottle (TCP Slow Start + AIMD)
│   │   └── parsers/                 # HTML parsers per entity
│   ├── cache/
│   │   └── valkey_cache.py          # ValkeyCache (SWR envelope, API/player cache)
│   ├── csv/
│   │   └── parsers/                 # CSV parsers for static data
│   ├── storage/
│   │   └── postgres_storage.py      # PostgresStorage (player profiles persistence)
│   └── tasks/
│       ├── valkey_broker.py         # ValkeyListBroker (taskiq broker over Valkey)
│       ├── valkey_task_queue.py     # ValkeyTaskQueue (SWR enqueue, dedup via SET NX)
│       ├── task_registry.py         # TASK_MAP shared dict (breaks circular import)
│       └── worker.py                # taskiq tasks + cron (refresh_*, cleanup_stale_players, check_new_hero)
├── api/                             # HTTP layer — FastAPI routers, models, middleware
│   ├── dependencies.py              # FastAPI dependency providers
│   ├── enums.py                     # API-layer enums (RouteTag, Profiler)
│   ├── docs.py                      # Redoc theme, render_documentation, setup_custom_openapi
│   ├── exception_handlers.py        # register_exception_handlers(app)
│   ├── helpers.py                   # overfast_internal_error, send_discord_webhook_message
│   ├── lifespan.py                  # FastAPI lifespan context manager
│   ├── middlewares.py               # Profiler middlewares (memray, pyinstrument, etc.)
│   ├── profiler.py                  # register_profiler(app, profiler)
│   ├── responses.py                 # ASCIIJSONResponse
│   ├── models/                      # Pydantic response models
│   │   ├── errors.py
│   │   ├── heroes.py
│   │   ├── maps.py
│   │   ├── players.py
│   │   ├── players_examples.py
│   │   ├── gamemodes.py
│   │   └── roles.py
│   └── routers/
│       ├── docs.py                  # / and /docs routes (Redoc + Swagger)
│       ├── heroes.py
│       ├── roles.py
│       ├── maps.py
│       ├── gamemodes.py
│       └── players.py
├── infrastructure/
│   ├── commands/
│   │   └── check_new_hero.py        # CLI script (also run as taskiq cron)
│   ├── decorators.py
│   ├── logger.py                    # loguru logger (overfast_logger)
│   └── metaclasses.py               # Singleton metaclass with clear_all()
└── monitoring/
    ├── metrics.py                   # Prometheus metrics
    └── middleware.py                # PrometheusMiddleware registration
```

### DDD layer rules

| Layer | May depend on | Must not depend on |
|---|---|---|
| `domain` | nothing outside stdlib | `adapters`, `api`, `infrastructure` |
| `adapters` | `domain` | `api` |
| `api` | `domain`, `adapters` (via DI) | — |
| `infrastructure` | anything | — |

### Request flow

```
Router (api/routers/)
  → get_* dependency (api/dependencies.py)
    → Service.get_or_fetch() (domain/services/)
      → CachePort.get()
        ├── Cache HIT (fresh)  → return immediately
        ├── Cache HIT (stale)  → return immediately + enqueue background refresh via TaskQueuePort
        └── Cache MISS         → BlizzardClientPort.fetch() → parse → CachePort.set() → return
```

### SWR (Stale-While-Revalidate) pattern

When `get_or_fetch` finds cached data whose age ≥ `staleness_threshold`, it serves the stale data immediately and enqueues a background refresh task via `ValkeyTaskQueue`. Deduplication is done with a Valkey `SET NX` so the same resource is never refreshed twice concurrently.

### Background worker

A separate `taskiq worker` process shares dependency injection with the API via `taskiq_fastapi`. It runs:
- `refresh_*` tasks — triggered by SWR enqueues
- `cleanup_stale_players` — daily cron at 03:00
- `check_new_hero` — daily cron at 02:00 (also runnable as a CLI script via `app/infrastructure/commands/check_new_hero.py`)

### Throttle (`app/adapters/blizzard/throttle.py`)

`BlizzardThrottle` implements TCP Slow Start + AIMD to self-regulate request rate against Blizzard:
- **Slow Start**: halves the inter-request delay every `throttle_slow_start_n_successes` consecutive 200 responses.
- **AIMD**: decreases delay by `throttle_aimd_delta` every `throttle_aimd_n_successes` consecutive 200 responses once below the slow-start threshold.
- **Penalty**: on a 403, delay is doubled and `ssthresh` is updated; penalty persists for `throttle_penalty_duration` seconds.
- Throttle state is persisted in Valkey so it survives restarts.

### Singleton pattern

`BlizzardClient`, `ValkeyCache`, `PostgresStorage`, and `BlizzardThrottle` all use the `Singleton` metaclass from `app.infrastructure.metaclasses`. Tests call `Singleton.clear_all()` in fixtures to reset state between runs.

---

## Code style and languages

- Python 3.14+
- 4-space indentation
- Explicit type hints on public APIs
- ty is the type checker: run `just check` to validate types
- Ruff is the linter/formatter: run `just lint` and `just format` before commits
- Naming:
  - snake_case for functions/variables
  - PascalCase for classes
  - UPPER_SNAKE_CASE for constants
- CSV keys and static file names use lowercase-hyphenated format to match the public URL schema

---

## Testing

- Tests use pytest with fixtures in `tests/conftest.py`
  - `client`: FastAPI TestClient (session-scoped)
  - `valkey_server`: `fakeredis.FakeAsyncRedis` in-memory cache
  - `Singleton.clear_all()` is called between tests to reset adapter singletons
  - External services and Valkey are auto-patched where needed
- Test structure mirrors the `app/` DDD layout (e.g. `tests/domain/services/`, `tests/adapters/blizzard/`)
- Coverage outputs to `htmlcov/`
- Test fixtures for Blizzard HTML responses live in `tests/fixtures/`

When changing behavior, run unit tests and ensure test coverage does not regress before proposing changes.

---

## Data files and static assets

- Hero data: `app/adapters/csv/data/heroes.csv`
- Game modes: `app/adapters/csv/data/gamemodes.csv`
- Maps: `app/adapters/csv/data/maps.csv`
- Map screenshots: `static/maps/<key>.jpg`

When updating CSVs or static assets, ensure filenames and `key` column values match the public URL schema.

---

## Configuration

- Configuration lives in `app/config.py` using Pydantic BaseSettings.
- Defaults are provided in `.env.dist`.
- Important settings: `APP_PORT`, `APP_BASE_URL`, `LOG_LEVEL`, `VALKEY_HOST`, `VALKEY_PORT`, and route-specific cache TTLs such as `HEROES_PATH_CACHE_TIMEOUT`, `CAREER_PATH_CACHE_TIMEOUT`, etc.
- Throttle-specific settings: `throttle_enabled`, `throttle_start_delay`, `throttle_min_delay`, `throttle_max_delay`, `throttle_slow_start_n_successes`, `throttle_aimd_n_successes`, `throttle_aimd_delta`, `throttle_penalty_delay`, `throttle_penalty_duration`.
- New config flags should be added to `app/config.py` and documented in `.env.dist`.

---

## Commits & PRs

- Use Conventional Commits (examples):
  - `feat:`, `fix:`, `build(deps):`, `chore:`, `docs:`
  - Scoped examples: `feat(players):`, `fix(maps):`
- Include a short, clear PR description with motivation and testing steps.
- If proposing breaking changes, call them out in the PR title and description and discuss with maintainers first.

---

## Agent behavior & safety guidelines

When an agent (automated assistant) works with this repository, follow these rules:

- Ask before writing or pushing changes:
  - Do not create branches, commits, or PRs unless explicitly asked and given required metadata (owner, repo, branch name, PR title, description).
- Reproduction-first approach:
  - If diagnosing an issue, try to reproduce locally (use `just test`, `just start`) or request logs/CI failure details from the user.
- Use provided commands and containerized workflows:
  - Prefer running commands inside the repository's development containers or with the provided scripts (just/make).
- Respect secrets and credentials:
  - Never attempt to access secrets, API keys, or private tokens. Do not add secrets to code or commits.
- Minimize assumptions:
  - If a change requires an environment-specific value (branch name, secret, remote), ask the maintainer.
- Safety checks before code changes:
  - Run type checker (`just check`), linter (`just lint`), and tests (`just test`) locally (or request CI run) before suggesting code to be merged.
- Be explicit about automated actions:
  - If an agent can open a PR, include a human-readable summary of what changed, why, how it was tested, and any follow-ups.
- Respect repository conventions:
  - Follow the code style, commit message style, and architecture patterns already in the repo.

---

## When to involve humans

- Design or API changes that affect public behavior or backwards compatibility
- Any change that requires secrets, credentials, or external access
- Permission to push branches, create PRs, or release new versions
- Interpreting ambiguous or incomplete requirements

---

## Troubleshooting & debugging tips

- For failing tests: run `just test -k <pattern>` and inspect `htmlcov/` and pytest output
- For caching issues: inspect `app/adapters/cache/valkey_cache.py` and Valkey/Nginx caches
- For throttle/rate-limit problems: check `app/adapters/blizzard/throttle.py`
- For parsing regressions: look into `app/adapters/blizzard/parsers/` (HTML) or `app/adapters/csv/parsers/` (static data) and compare to fixtures in `tests/fixtures/`
- For worker/background task issues: inspect `app/adapters/tasks/worker.py`

---

## Contact & contribution notes

- Use conventional issue/PR workflow for contributions and bug reports
- Provide reproducible steps, environment details, and relevant logs in issues
- For large changes, open a draft PR and request review from maintainers

---
