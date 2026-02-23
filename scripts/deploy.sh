#!/bin/bash
# Zero-downtime deploy script for OverFast API
# Called by /opt/deploy-overfast.sh after git reset and .env sync.
# Strategy: keep nginx up throughout; rolling-restart app+worker only.
# Nginx is only recreated when its image actually changed.
set -euo pipefail

LOG_FILE="/var/log/overfast-deploy.log"
COMPOSE_PROJECT="overfast-api"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Poll a service until its health status is "healthy".
# Usage: wait_healthy <service> [max_wait_seconds]
wait_healthy() {
    local service=$1 max_wait=${2:-90} waited=0
    log "Waiting for '$service' to become healthy (timeout ${max_wait}s)..."
    while [ "$waited" -lt "$max_wait" ]; do
        local id health
        id=$(docker compose ps -q "$service" 2>/dev/null | head -1)
        if [ -n "$id" ]; then
            health=$(docker inspect "$id" --format '{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
            if [ "$health" = "healthy" ]; then
                log "  '$service' is healthy after ${waited}s."
                return 0
            fi
        fi
        sleep 3
        waited=$((waited + 3))
    done
    log "ERROR: '$service' did not become healthy within ${max_wait}s."
    docker compose ps "$service" 2>&1 | tee -a "$LOG_FILE" || true
    return 1
}

# ── Step 1: Capture the currently running nginx image ID (before build) ──────
log "Capturing current nginx image ID..."
NGINX_CONTAINER_ID=$(docker compose ps -q nginx 2>/dev/null | head -1 || true)
if [ -n "$NGINX_CONTAINER_ID" ]; then
    NGINX_IMAGE_BEFORE=$(docker inspect "$NGINX_CONTAINER_ID" --format '{{.Image}}' 2>/dev/null || echo "")
    log "  Current nginx image: ${NGINX_IMAGE_BEFORE:-<none>}"
else
    NGINX_IMAGE_BEFORE=""
    log "  nginx container not running yet."
fi

# ── Step 2: Build all images (stack stays live during build) ──────────────────
log "Building Docker images..."
docker compose build 2>&1 | tee -a "$LOG_FILE"
log "Build complete."

# ── Step 3: Rolling restart — app + worker only, nginx untouched ──────────────
log "Rolling restart: app + worker (nginx stays up)..."
docker compose up -d --no-deps app worker 2>&1 | tee -a "$LOG_FILE"

# ── Step 4: Wait for app to be healthy ────────────────────────────────────────
wait_healthy app 90

# ── Step 5: Decide how to handle nginx ───────────────────────────────────────
# Compare the image the running nginx container was launched from against
# the image that docker compose build just produced.
NGINX_IMAGE_AFTER=$(docker compose images nginx --format json 2>/dev/null \
    | python3 -c "import sys,json; imgs=json.load(sys.stdin); print(imgs[0]['ID'] if imgs else '')" 2>/dev/null \
    || docker images "${COMPOSE_PROJECT}-nginx" --format '{{.ID}}' | head -1 \
    || true)

log "  Nginx image before: ${NGINX_IMAGE_BEFORE:-<none>}"
log "  Nginx image after : ${NGINX_IMAGE_AFTER:-<none>}"

if [ -z "$NGINX_CONTAINER_ID" ]; then
    # nginx was not running at all — bring it up fresh
    log "nginx was not running. Starting nginx..."
    docker compose up -d --no-deps nginx 2>&1 | tee -a "$LOG_FILE"
elif [ -n "$NGINX_IMAGE_AFTER" ] && [ "$NGINX_IMAGE_BEFORE" != "$NGINX_IMAGE_AFTER" ]; then
    # Image changed — recreate container (sub-second gap)
    log "nginx image changed. Recreating nginx container..."
    docker compose up -d --no-deps nginx 2>&1 | tee -a "$LOG_FILE"
else
    # Image unchanged — graceful in-place config reload (zero-downtime)
    log "nginx image unchanged. Reloading nginx config in-place..."
    docker compose exec -T nginx nginx -s reload 2>&1 | tee -a "$LOG_FILE"
fi

# ── Step 6: Final health assertion ────────────────────────────────────────────
log "Verifying all containers are healthy..."
sleep 5
if docker compose ps | grep -E "unhealthy|Exit [^0]"; then
    log "ERROR: One or more containers are unhealthy after deploy!"
    docker compose ps 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

log "Deployment completed successfully!"
docker compose ps 2>&1 | tee -a "$LOG_FILE"
