# CLAUDE.md

Guidance for Claude Code (claude.ai/code) in this repository.

**Read [AGENTS.md](./AGENTS.md) first.** It is the detailed and current reference for the
architecture (four DDD layers, dependency direction), the `just` command set, code style, testing
and coverage rules. This file carries only what AGENTS.md does not: what makes this a *fork*, and
how it reaches production.

## This is a deliberately divergent fork

Forked from [TeKrop/overfast-api](https://github.com/TeKrop/overfast-api). Since 2026-08-29 the
divergence is intentional: upstream develops too slowly, and **`app/` is fork-owned** — fixes land
here directly rather than as upstream PRs. The nightly auto-merge workflow and its `.gitattributes`
merge drivers have been removed.

Upstream is still the fastest source of *Blizzard compatibility* — new heroes, maps and competitive
divisions usually ship there within days, and that work is time-critical (a new rank makes
`CompetitiveDivision(...)` raise; a new hero leaves `/heroes` incomplete). Track it as a
**cherry-pick source**, not a merge parent:

```bash
git remote add upstream https://github.com/TeKrop/overfast-api.git  # once
git fetch upstream --no-tags
git log --oneline HEAD..upstream/main -- app/domain/parsers/ app/domain/utils/data/
git cherry-pick <sha>
```

Roughly 20 commits a year are worth taking; the rest of upstream's traffic is dependabot noise.

## Deployment — this repo is live

- **Never push directly to `main`.** A push to `main` runs
  `.github/workflows/release.yaml`: semantic-release → smoke test → zero-downtime SSH deploy to the
  VPS. Always work on a branch and open a PR.
- To redeploy current `main` without a code change, run that workflow manually
  (`workflow_dispatch`) from the Actions tab.
- **Never deploy with `docker compose down`.** It drops the containers and with them the caches:
  valkey loses the API cache and every player profile has to be refetched from Blizzard behind the
  throttle. `scripts/deploy.sh` rolls containers instead and reloads nginx rather than restarting it.

## Verifying changes

AGENTS.md covers `just check` / `just lint` / `just test`. Two extra gates matter here, because unit
tests pass against captured fixtures and prove nothing about the live stack:

```bash
bash scripts/smoke-test.sh        # boots the compose stack, validates the static endpoints
bash scripts/persistence-test.sh  # asserts postgres survives a container lifecycle
```

Both run in CI on every PR. Running the suite outside Docker needs `POSTGRES_PASSWORD` —
`app/config.py` builds `Settings` at import time, so pytest fails during collection without it.

## Things that bite

- The taskiq **worker runs the same `app/api/lifespan.py`** as the API process. Anything there that
  touches the shared cache must be guarded with `if not broker.is_worker_process`.
- **Postgres holds only cache.** `static_data` and `player_profiles` are both regenerable Blizzard
  content, so losing them costs refetch time, not data. The volume must stay mounted at the PGDATA
  path itself — `postgres:17` declares `VOLUME /var/lib/postgresql/data` and will shadow a mount on
  the parent with a throwaway anonymous volume.
- **Hitpoint columns in `heroes.csv` are hand-maintained.** Blizzard publishes them nowhere, so they
  rot silently after balance patches and nothing in the test suite can catch it.
- The **domain layer must stay framework-agnostic** — `fastapi` is a banned import there, enforced
  by ruff's `TID251`.
