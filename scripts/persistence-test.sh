#!/bin/bash
# Postgres persistence e2e: proves the database survives a container lifecycle
# and actually lives in the *named* volume.
#
# The smoke test only exercises static endpoints, so it stayed green while the
# cluster was silently written to an anonymous volume (pg-data mounted at
# /var/lib/postgresql, while postgres:17 declares VOLUME /var/lib/postgresql/data
# and shadows it). That anonymous volume is orphaned on recreation and destroyed
# by `docker compose down -v`, so the cache cold-started for no visible reason.
#
# Expects a stack that is already up (e.g. after scripts/smoke-test.sh).
# Restarts the stack — do not run against production.
set -euo pipefail

PG_USER="${POSTGRES_USER:-overfast}"
PG_DB="${POSTGRES_DB:-overfast}"
ERRORS=0

fail() {
    echo "  FAIL: $1"
    ERRORS=$((ERRORS + 1))
}

psql_q() {
    docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -tAc "$1"
}

wait_for_postgres() {
    for _ in $(seq 1 30); do
        if docker compose exec -T postgres pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    echo "::error::postgres did not become ready"
    docker compose logs --tail=50 postgres
    exit 1
}

# ── Check 1: the cluster lives in the named volume ───────────────────────────
# Structural check. Explains *why* check 2 fails when it does.
echo "=== Check 1: PGDATA is backed by the named pg-data volume ==="
PG_CID="$(docker compose ps -q postgres)"
if [ -z "$PG_CID" ]; then
    echo "::error::postgres container is not running — start the stack first"
    exit 1
fi

PGDATA_PATH="$(docker compose exec -T postgres sh -c 'echo $PGDATA' | tr -d '\r\n')"
echo "  PGDATA=$PGDATA_PATH"

DATA_VOLUME="$(docker inspect "$PG_CID" \
    --format "{{range .Mounts}}{{if eq .Destination \"${PGDATA_PATH}\"}}{{.Name}}{{end}}{{end}}")"

if [ -z "$DATA_VOLUME" ]; then
    fail "no volume is mounted at $PGDATA_PATH — the cluster is in the container layer"
elif ! echo "$DATA_VOLUME" | grep -q 'pg-data$'; then
    fail "PGDATA is backed by anonymous volume ${DATA_VOLUME:0:12}… — not the named pg-data volume"
else
    echo "  OK: $DATA_VOLUME"
fi

# ── Check 2: data survives down/up ───────────────────────────────────────────
echo "=== Check 2: data survives a compose down/up cycle ==="
STATIC_ROWS_BEFORE="$(psql_q 'SELECT count(*) FROM static_data;' | tr -d '\r')"
echo "  static_data rows before: $STATIC_ROWS_BEFORE"
[ "$STATIC_ROWS_BEFORE" -gt 0 ] || fail "static_data is empty — run scripts/smoke-test.sh first"

psql_q 'CREATE TABLE IF NOT EXISTS _persistence_probe (id INT PRIMARY KEY);' >/dev/null
psql_q 'INSERT INTO _persistence_probe VALUES (1) ON CONFLICT DO NOTHING;' >/dev/null

echo "  cycling the stack (down without -v, then up)…"
docker compose down >/dev/null 2>&1
docker compose up -d >/dev/null 2>&1
wait_for_postgres

PROBE="$(psql_q "SELECT count(*) FROM _persistence_probe WHERE id = 1;" 2>/dev/null | tr -d '\r' || echo 0)"
if [ "$PROBE" = "1" ]; then
    echo "  OK: probe row survived"
    psql_q 'DROP TABLE IF EXISTS _persistence_probe;' >/dev/null
else
    fail "probe row did not survive the restart — the database was recreated empty"
fi

STATIC_ROWS_AFTER="$(psql_q 'SELECT count(*) FROM static_data;' 2>/dev/null | tr -d '\r' || echo 0)"
echo "  static_data rows after: $STATIC_ROWS_AFTER"
[ "$STATIC_ROWS_AFTER" = "$STATIC_ROWS_BEFORE" ] \
    || fail "static_data went from $STATIC_ROWS_BEFORE to $STATIC_ROWS_AFTER rows — cache cold-started"

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo "::error::$ERRORS persistence error(s)"
    exit 1
fi
echo "Postgres persistence verified."
