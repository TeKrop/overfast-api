# Repository Guidelines

## Project Structure & Module Organization
Application code lives in `app/`, grouped by feature modules such as `app/api`, `app/common`, and parser helpers. Game data is maintained through the CSV files in `app/heroes/data`, `app/gamemodes/data`, and `app/maps/data`; keep filenames and the `key` column aligned with public URLs. Static screenshots or icons belong under `static/` (`static/maps/<key>.jpg`). Automated and integration tests sit in `tests/` with fixtures updated via `tests/update_test_fixtures`. Root-level tooling (`justfile`, `Makefile`, `docker-compose.yml`, `.env.dist`) orchestrates local Docker workflows, while generated artifacts land in `logs/` and `htmlcov/`.

## Build, Test, and Development Commands
Run `just build` once to create dev images, then `just start` for the autoreloading FastAPI app on `localhost:8000`. `just start_testing` launches the nginx + reverse-proxy profile on port `8080`, and `just down` stops all containers. Production-style smoke tests use `just up` (or `make up`). Quality automation is exposed as `just lint` (`uvx ruff check --fix`), `just format` (`uvx ruff format`), `just test` (pytest with coverage and `-n auto`), plus `just shell` or `just exec` for interactive debugging.

## Coding Style & Naming Conventions
Target Python 3.12+, keep four-space indentation, and prefer explicit type hints on new public APIs. Ruff handles linting and formatting; run `just lint` and `just format` before every commit or install the bundled pre-commit hook (`pre-commit install`). Modules, variables, and functions stay `snake_case`, classes use `PascalCase`, and constants or settings are `UPPER_SNAKE_CASE`. When touching CSV datasets or static files, use lowercase, hyphenated keys that match the OverFast URL schema. Document new configuration flags inside `app/config.py` and add defaults to `.env.dist`.

## Testing Guidelines
Tests run with `pytest`, driven through `just test`. Scope suites with `just test tests/api/test_players.py` or `make test PYTEST_ARGS="tests/common"`. Name files `test_<area>.py` and preserve fixture helpers near the domain they validate. Route changes should include FastAPI client tests plus parser or CLI coverage to keep the README coverage badge meaningful. Store generated HTML coverage in `htmlcov/` and clean it only when necessary.

## Commit & Pull Request Guidelines
Commits use a Conventional Commit tone (`feat:`, `fix:`, `build(deps):`, etc.) with optional scopes such as `feat(players):`. Keep diffs focused, include related CSV/static updates, and reference GitHub issues when applicable. Before submitting a PR, ensure `just lint`, `just format`, and `just test` succeed, describe the motivation, list validation steps, and attach screenshots or sample API payloads when responses change. Highlight required `.env` updates or migrations so reviewers can reproduce your environment.
