# CLAUDE.md

**Full guidance is in `AGENTS.md`** — read it before making changes. This file is a quick-reference summary.

---

## Commands

All commands use `just` (or `make` as a fallback). Linting/type-checking run locally; tests run inside Docker.

```bash
just build                                         # Build Docker images (required first)
just start                                         # Run app with autoreload on localhost:8000
just check                                         # Type check with ty (uv run ty check)
just lint                                          # Ruff linter with --fix + import-linter contracts
just format                                        # Ruff formatter
just test                                          # All tests with coverage (-n auto)
just test tests/domain/services/                   # Specific directory
just test tests/adapters/blizzard/test_client.py   # Specific file
just test "tests/ -k test_get_hero_by_key"         # Match by keyword
just exec "python -m tests.update_test_fixtures"   # Refresh HTML/JSON parser fixtures
```

Always run `just check`, `just lint`, and `just test` before proposing changes. CI enforces 80% minimum coverage.

---

## Architecture

FastAPI app following strict DDD layering — dependencies flow inward only:

```
main, worker → api → adapters → domain → monitoring → infrastructure → config
```

**Request flow:**
```
Router → get_* dependency (api/dependencies.py)
  → Service.get_or_fetch()           # Stale-While-Revalidate orchestration
    → CachePort.get()
      ├── HIT (fresh)  → return immediately
      ├── HIT (stale)  → return + enqueue background refresh via TaskQueuePort
      └── MISS         → BlizzardClientPort.fetch() → parse → CachePort.set() → return
```

---

## Key conventions

**Error handling:** Use `raise Exc(msg) from exc` for chaining. Infrastructure errors caught with `except Exception:  # noqa: BLE001`, never crash requests.

**Logging:** `from app.infrastructure.logger import logger` (loguru). Always use brace-style: `logger.info("fetching {}", url)`. Never f-strings or `%s` in log calls.

**Type hints:** `X | Y` unions, `X | None` for optional, `TYPE_CHECKING` guard for type-only imports. All public function signatures must be fully typed.

**Singletons:** `BlizzardClient`, `ValkeyCache`, `PostgresStorage`, `BlizzardThrottle` use `metaclass=Singleton`. Tests call `Singleton.clear_all()` via autouse fixture.

**Tests:** Follow Arrange / Act / Assert with blank lines (no comment labels). Never inline Act inside `assert`. When using `with patch(...)`, Act is the last line inside the block; Assert comes after.

**Static data:** Adding a new hero/map/gamemode only requires updating the CSV — `HeroKey`, `MapKey`, `MapGamemode` enums are generated dynamically at import time.

**Commits:** Conventional Commits (`feat:`, `fix:`, `build(deps):`, `chore:`, `docs:`). Scoped variants allowed (`feat(players):`).
