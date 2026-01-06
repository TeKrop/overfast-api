# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OverFast API is a FastAPI-based Overwatch 2 data API that scrapes Blizzard pages to provide data about heroes, game modes, maps, and player statistics. It uses a three-tier caching strategy backed by Valkey, with Nginx/OpenResty as a reverse proxy.

## Build, Test, and Development Commands

```bash
just build              # Build Docker images (required first)
just start              # Run app with autoreload on localhost:8000
just start_testing      # Run with nginx reverse proxy on localhost:8080
just down               # Stop all containers
just lint               # Run ruff linter with --fix
just format             # Run ruff formatter
just test               # Run all tests with coverage
just test tests/heroes  # Run specific test directory
just test tests/heroes/test_heroes_route.py  # Run specific test file
just shell              # Interactive shell in container
just exec "command"     # Execute command in container
```

Make alternatives available: `make build`, `make start`, `make test PYTEST_ARGS="tests/common"`, etc.

## Architecture

### Router → Controller → Parser Pattern

Each API endpoint follows this flow:
1. **Router** (`module/router.py`): Defines FastAPI endpoints, request validation
2. **Controller** (`module/controllers/`): Orchestrates parsing, caching, response building
3. **Parser** (`module/parsers/`): Retrieves and parses data from Blizzard or CSV files

### Module Structure

Each feature module (heroes, players, roles, gamemodes, maps) in `app/` follows:
```
module/
├── router.py           # FastAPI routes
├── models.py           # Pydantic response models
├── enums.py            # Enum definitions
├── controllers/        # Request processors (inherit AbstractController)
├── parsers/            # Data extractors (inherit AbstractParser)
└── data/               # CSV files for static data (if applicable)
```

### Key Components

- **CacheManager** (`app/cache_manager.py`): Singleton managing API Cache, Player Cache, and Unknown Players Cache via Valkey
- **OverFastClient** (`app/overfast_client.py`): Async HTTP client with Blizzard rate limit handling
- **AbstractController** (`app/controllers.py`): Base class orchestrating parser execution and caching
- **AbstractParser** (`app/parsers.py`): Base class for data extraction; `CSVParser` subclass for local CSV files
- **Settings** (`app/config.py`): Pydantic BaseSettings with all configuration

### Caching Strategy

- **API Cache**: HTTP response caching with TTL per route (nginx stores in Valkey)
- **Player Cache**: Parsed player profiles with 3-day TTL, only used if profile unchanged
- **Unknown Players Cache**: Negative cache for non-existent players (1-hour TTL)

## Code Style

- Python 3.14+, 4-space indentation, explicit type hints on public APIs
- Ruff handles all linting and formatting - run `just lint` and `just format` before commits
- snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
- CSV keys and static file names use lowercase-hyphenated format matching URL schema

## Testing

Tests use pytest with fixtures in `tests/conftest.py`:
- `client`: FastAPI TestClient (session-scoped)
- `valkey_server`: FakeRedis in-memory cache
- Auto-patching of Valkey and external services before each test

Coverage output goes to `htmlcov/`. Test fixtures for Blizzard HTML responses are in `tests/fixtures/`.

## Data Files

- Hero stats: `app/heroes/data/heroes.csv`
- Game modes: `app/gamemodes/data/gamemodes.csv`
- Maps: `app/maps/data/maps.csv`
- Map screenshots: `static/maps/<key>.jpg`

When updating these, ensure filenames and `key` column values match the public URL schema.

## Configuration

New config flags go in `app/config.py` with defaults in `.env.dist`. Key settings:
- `APP_PORT`, `APP_BASE_URL`, `LOG_LEVEL`
- `VALKEY_HOST`, `VALKEY_PORT`
- Cache TTLs: `HEROES_PATH_CACHE_TIMEOUT`, `CAREER_PATH_CACHE_TIMEOUT`, etc.

## Commits

Use Conventional Commits: `feat:`, `fix:`, `build(deps):`, `chore:`, `docs:` with optional scopes like `feat(players):`.
