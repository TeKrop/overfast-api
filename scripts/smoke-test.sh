#!/bin/bash
# Full-stack smoke test: boots the compose stack from .env.dist defaults and
# validates the static endpoints end to end through nginx.
#
# Single source of truth for build.yml (pull requests), release.yaml (deploy
# gate) and sync-upstream.yml (nightly upstream merge). These three used to
# carry their own copy of this logic and drifted apart — the release copy was
# missing the POSTGRES_PASSWORD line, which let a credential mismatch reach
# the deploy gate unnoticed.
#
# Runnable locally: `bash scripts/smoke-test.sh` (overwrites .env).
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
TIMEOUT="${TIMEOUT:-150}"
INTERVAL=5
ERRORS=0

fetch() {
    curl -sf --compressed "$BASE_URL$1"
}

fail() {
    echo "  FAIL: $1"
    ERRORS=$((ERRORS + 1))
}

# ── Step 1: .env from shipped defaults ───────────────────────────────────────
# .env.dist ships POSTGRES_PASSWORD/GRAFANA_ADMIN_PASSWORD empty on purpose
# (docker-compose.yml requires them via ${VAR:?}), so supply test values.
echo "=== Creating .env from defaults ==="
# Keep a local developer .env recoverable — this script is runnable by hand.
# Plain `[ -f .env ] && ...` would abort under `set -e` when no .env exists.
if [ -f .env ]; then
    cp .env .env.smoke-backup
    echo "  existing .env saved to .env.smoke-backup"
fi
# One non-in-place pass: `sed -i'' -e` is read by BSD sed (macOS) as a backup
# suffix of "-e", which left a credential-carrying .env-e behind on every run.
sed -e 's/^APP_PORT=.*/APP_PORT=8080/' \
    -e 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=ci-test-password/' \
    -e 's/^GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=ci-test-password/' \
    .env.dist > .env

# ── Step 2: Build and start ──────────────────────────────────────────────────
echo "=== Building and starting services ==="
docker compose build
docker compose up -d

# ── Step 3: Wait for the core services ───────────────────────────────────────
echo "=== Waiting for core services (app, nginx, valkey) ==="
SERVICES="app nginx valkey"
READY=false

for i in $(seq 1 $((TIMEOUT / INTERVAL))); do
    HEALTHY=0
    for SERVICE in $SERVICES; do
        STATUS=$(docker compose ps --format json | jq -rs \
            "[.[] | select(.Service == \"$SERVICE\")] | .[0].Health // \"starting\"")
        [ "$STATUS" = "healthy" ] && HEALTHY=$((HEALTHY + 1))
    done

    echo "[$((i * INTERVAL))/${TIMEOUT}s] $HEALTHY/3 services healthy"
    if [ "$HEALTHY" -eq 3 ]; then
        READY=true
        break
    fi
    sleep $INTERVAL
done

if [ "$READY" != true ]; then
    echo "::error::Services did not become healthy within ${TIMEOUT}s"
    docker compose ps
    docker compose logs --tail=200
    exit 1
fi

# ── Step 4: Validate the static endpoints ────────────────────────────────────
# Every check is non-fatal so one run reports every problem at once; the
# accumulated ERRORS count decides the exit status.
echo "=== GET / ==="
BODY=$(fetch "/") || fail "/ not reachable"
echo "$BODY" | grep -q "redoc" || fail "/ does not contain redoc HTML"

echo "=== GET /openapi.json ==="
BODY=$(fetch "/openapi.json") || fail "/openapi.json not reachable"
echo "$BODY" | jq -e '.openapi' >/dev/null || fail "missing openapi version field"
echo "$BODY" | jq -e '.paths | keys | length > 5' >/dev/null || fail "too few paths in spec"

echo "=== GET /roles ==="
BODY=$(fetch "/roles") || fail "/roles not reachable"
COUNT=$(echo "$BODY" | jq 'length')
[ "$COUNT" -eq 3 ] || fail "expected 3 roles, got $COUNT"
KEYS=$(echo "$BODY" | jq -r '.[].key' | sort | tr '\n' ',')
[ "$KEYS" = "damage,support,tank," ] || fail "role keys mismatch: $KEYS"
echo "$BODY" | jq -e 'all(has("key","name","icon","description"))' >/dev/null \
    || fail "roles missing required fields"
echo "$BODY" | jq -e 'all(.icon | startswith("http"))' >/dev/null \
    || fail "role icons are not valid URLs"
echo "  $COUNT roles"

echo "=== GET /gamemodes ==="
BODY=$(fetch "/gamemodes") || fail "/gamemodes not reachable"
COUNT=$(echo "$BODY" | jq 'length')
[ "$COUNT" -ge 10 ] || fail "expected >=10 gamemodes, got $COUNT"
echo "$BODY" | jq -e 'all(has("key","name","icon","description","screenshot"))' >/dev/null \
    || fail "gamemodes missing required fields"
echo "$BODY" | jq -e 'all(.description | length > 10)' >/dev/null \
    || fail "gamemode descriptions too short or empty"
echo "$BODY" | jq -e 'map(.key) | contains(["control","escort","push"])' >/dev/null \
    || fail "known gamemodes (control, escort, push) not found"
echo "  $COUNT gamemodes"

echo "=== GET /maps ==="
BODY=$(fetch "/maps") || fail "/maps not reachable"
COUNT=$(echo "$BODY" | jq 'length')
[ "$COUNT" -ge 40 ] || fail "expected >=40 maps, got $COUNT"
echo "$BODY" | jq -e 'all(has("key","name","screenshot","gamemodes","location"))' >/dev/null \
    || fail "maps missing required fields"
echo "$BODY" | jq -e 'all(.gamemodes | length >= 1)' >/dev/null \
    || fail "some maps have no gamemodes"
echo "$BODY" | jq -e 'all(.screenshot | startswith("http"))' >/dev/null \
    || fail "map screenshots are not valid URLs"
echo "$BODY" | jq -e 'map(.key) | contains(["ilios","dorado","kings-row"])' >/dev/null \
    || fail "known maps (ilios, dorado, kings-row) not found"
echo "  $COUNT maps"

echo "=== GET /heroes ==="
BODY=$(fetch "/heroes") || fail "/heroes not reachable"
COUNT=$(echo "$BODY" | jq 'length')
[ "$COUNT" -ge 40 ] || fail "expected >=40 heroes, got $COUNT"
echo "$BODY" | jq -e 'all(has("key","name","portrait","role"))' >/dev/null \
    || fail "heroes missing required fields"
echo "$BODY" | jq -e 'all(.role | IN("damage","support","tank"))' >/dev/null \
    || fail "heroes have invalid roles"
echo "$BODY" | jq -e 'all(.portrait | startswith("http"))' >/dev/null \
    || fail "hero portraits are not valid URLs"
echo "$BODY" | jq -e 'map(.key) | contains(["ana","tracer","reinhardt"])' >/dev/null \
    || fail "known heroes (ana, tracer, reinhardt) not found"
for ROLE in damage support tank; do
    ROLE_COUNT=$(echo "$BODY" | jq "[.[] | select(.role == \"$ROLE\")] | length")
    [ "$ROLE_COUNT" -ge 5 ] || fail "only $ROLE_COUNT $ROLE heroes (expected >=5)"
done
echo "  $COUNT heroes"

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo "::error::$ERRORS validation error(s)"
    docker compose logs --tail=200
    exit 1
fi
echo "All endpoint validations passed."
