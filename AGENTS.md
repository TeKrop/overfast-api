# AGENTS.md

Guidance for automated assistants and code agents (Copilot, Claude, ChatGPT, bots, or any automated code-review/run agents) when interacting with this repository.

This document is intended to be a concise, repository-specific checklist and reference so agents can work safely and productively with the codebase.

---

## Project overview

OverFast API is a FastAPI-based Overwatch data API that scrapes Blizzard pages to provide data about heroes, game modes, maps, and player statistics. It uses a three-tier caching strategy backed by Valkey, with Nginx/OpenResty as a reverse proxy.

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
just test tests/heroes  # Run a specific test directory
just test tests/heroes/test_heroes_route.py  # Run a specific test file
just shell              # Interactive shell in container
just exec "command"     # Execute command in container
```

Make alternatives available: `make build`, `make start`, `make test PYTEST_ARGS="tests/common"`, etc.

If you need to run anything that modifies the repo (commits, pushes, PRs), explicitly ask the human maintainer for permission, branch name, and commit message.

---

## Architecture summary

Pattern used across modules:
- Router → Controller → Parser
  1. Router (`module/router.py`): FastAPI endpoints, request validation
  2. Controller (`module/controllers/`): Orchestrates parsing, caching, response building
  3. Parser (`module/parsers/`): Retrieves and parses data from Blizzard or CSV files

Module layout (per feature):
```
module/
├── router.py           # FastAPI routes
├── models.py           # Pydantic response models
├── enums.py            # Enum definitions
├── controllers/        # Request processors (inherit AbstractController)
├── parsers/            # Data extractors (inherit AbstractParser)
└── data/               # CSV files for static data (if applicable)
```

Key components:
- CacheManager (`app/cache_manager.py`): Singleton that manages API Cache, Player Cache, and Unknown Players Cache via Valkey
- OverFastClient (`app/overfast_client.py`): Async HTTP client with Blizzard rate-limit handling
- AbstractController (`app/controllers.py`): Base class that orchestrates parser execution and caching
- AbstractParser (`app/parsers.py`): Base class for data extraction; `CSVParser` subclass for local CSV files
- Settings (`app/config.py`): Pydantic BaseSettings with configuration values

Caching strategy:
- API Cache: HTTP response caching with TTL per route
- Player Cache: Parsed player profiles with ~3-day TTL; only used if profile unchanged
- Unknown Players Cache: Negative cache (non-existent players) with short TTL (~1 hour)

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
  - `valkey_server`: FakeRedis in-memory cache
  - External services and Valkey are auto-patched where needed
- Coverage outputs to `htmlcov/`
- Test fixtures for Blizzard HTML responses live in `tests/fixtures/`

When changing behavior, run unit tests and ensure test coverage does not regress before proposing changes.

---

## Data files and static assets

- Hero stats: `app/heroes/data/heroes.csv`
- Game modes: `app/gamemodes/data/gamemodes.csv`
- Maps: `app/maps/data/maps.csv`
- Map screenshots: `static/maps/<key>.jpg`

When updating CSVs or static assets, ensure filenames and `key` column values match the public URL schema.

---

## Configuration

- Configuration lives in `app/config.py` using Pydantic BaseSettings.
- Defaults are provided in `.env.dist`.
- Important settings: `APP_PORT`, `APP_BASE_URL`, `LOG_LEVEL`, `VALKEY_HOST`, `VALKEY_PORT`, and route-specific cache TTLs such as `HEROES_PATH_CACHE_TIMEOUT`, `CAREER_PATH_CACHE_TIMEOUT`, etc.
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
- For caching issues: inspect `app/cache_manager.py` and Valkey/Nginx caches
- For rate-limit problems: check `app/overfast_client.py` for retry/backoff logic
- For parsing regressions: look into module `parsers/` and compare to fixtures in `tests/fixtures/`

---

## Contact & contribution notes

- Use conventional issue/PR workflow for contributions and bug reports
- Provide reproducible steps, environment details, and relevant logs in issues
- For large changes, open a draft PR and request review from maintainers

---
