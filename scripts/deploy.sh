#!/bin/bash
# Zero-downtime deploy script for OverFast API.
# Called by /opt/deploy-overfast.sh after git reset and .env sync.
#
# Order:
#   build (--pull) → postgres up → valkey up → app+worker+scheduler up
#   → nginx (reload-or-recreate). Nginx never goes through a hard
#   restart unless its image changed.
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

# Capture the image ID a service's running container was launched from.
# Used to detect whether `docker compose build` produced a new image
# that the running container is not yet using. Empty string if the
# service is not running.
running_image_id() {
    local service=$1 cid
    cid=$(docker compose ps -q "$service" 2>/dev/null | head -1 || true)
    [ -z "$cid" ] && return 0
    docker inspect "$cid" --format '{{.Image}}' 2>/dev/null || true
}

# ── Step 1: Snapshot running image IDs before we rebuild ─────────────────────
log "Capturing current image IDs..."
NGINX_IMAGE_BEFORE=$(running_image_id nginx)
VALKEY_IMAGE_BEFORE=$(running_image_id valkey)
log "  nginx  : ${NGINX_IMAGE_BEFORE:-<none>}"
log "  valkey : ${VALKEY_IMAGE_BEFORE:-<none>}"

# ── Step 2: Build all images, pulling fresh base layers ──────────────────────
# --pull: re-fetch FROM bases of the services we build ourselves
# (python, openresty, valkey/valkey:9-alpine, ...). Without it we silently
# skip security/feature updates whenever the registry tag is unchanged but
# its content moved.
log "Building Docker images (--pull)..."
docker compose build --pull 2>&1 | tee -a "$LOG_FILE"
log "Build complete."

# ── Step 3: Ensure postgres is running and healthy ───────────────────────────
# postgres is the only service in the default profile without a `build:`
# context, so `build --pull` above never touches it and `up -d` reuses
# whatever is in the local image store. Pull it explicitly, otherwise the
# tag stays frozen at whatever was first pulled onto the host.
# Non-fatal: a registry outage or rate limit must not abort a deploy that
# has no postgres change to apply.
log "Pulling postgres base image..."
docker compose pull postgres 2>&1 | tee -a "$LOG_FILE" \
    || log "WARNING: postgres pull failed, continuing with the local image."

# `docker compose up -d --no-deps` is idempotent: only recreates the
# container when image or config changed.
log "Ensuring postgres is running..."
docker compose up -d --no-deps postgres 2>&1 | tee -a "$LOG_FILE"
wait_healthy postgres 120

# ── Step 4: Recreate valkey if its image changed ─────────────────────────────
# valkey is a dependency of app/worker/scheduler — must be on the new
# image before they restart, otherwise app keeps talking to the old
# valkey while a new one is built but never started.
log "Reconciling valkey container with built image..."
docker compose up -d --no-deps valkey 2>&1 | tee -a "$LOG_FILE"
VALKEY_IMAGE_AFTER=$(running_image_id valkey)
if [ "$VALKEY_IMAGE_BEFORE" != "$VALKEY_IMAGE_AFTER" ]; then
    log "  valkey image changed: ${VALKEY_IMAGE_BEFORE:-<none>} -> $VALKEY_IMAGE_AFTER"
fi
wait_healthy valkey 60

# ── Step 5: Zero-downtime app swap (rolling) ─────────────────────────────────
# Strategy: scale 'app' to 2 first so a new container starts alongside the
# old one and nginx's upstream pool sees both. Once the new container is
# healthy, stop the old one. nginx re-resolves the 'app' DNS via its
# `resolver` directive (valid=5s) so requests fail over to the new IP
# without a config reload.
#
# worker + scheduler don't carry user requests, so we restart them in place.
log "Zero-downtime app swap..."

OLD_APP=$(docker compose ps -q app 2>/dev/null | head -1 || true)
OLD_RUNNING=false
if [ -n "$OLD_APP" ] && docker inspect "$OLD_APP" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then
    OLD_RUNNING=true
fi

if [ "$OLD_RUNNING" = "true" ]; then
    log "  scaling app to 2 (old=$OLD_APP)..."
    docker compose up -d --no-deps --no-recreate --scale app=2 app 2>&1 | tee -a "$LOG_FILE"

    # New container = the one that is not OLD_APP.
    NEW_APP=""
    for cid in $(docker compose ps -q app); do
        if [ "$cid" != "$OLD_APP" ]; then
            NEW_APP=$cid
            break
        fi
    done
    log "  new app container: ${NEW_APP:-<none>}"

    if [ -n "$NEW_APP" ]; then
        log "  waiting for new app instance to be healthy..."
        waited=0
        new_healthy=false
        while [ "$waited" -lt 90 ]; do
            health=$(docker inspect "$NEW_APP" --format '{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
            if [ "$health" = "healthy" ]; then
                log "    new app healthy after ${waited}s."
                new_healthy=true
                break
            fi
            sleep 3
            waited=$((waited + 3))
        done
        if [ "$new_healthy" != "true" ]; then
            log "ERROR: new app instance never became healthy. Stopping it; old container keeps serving."
            docker stop "$NEW_APP" >/dev/null
            docker rm "$NEW_APP" >/dev/null
            docker compose up -d --no-deps --no-recreate --scale app=1 app >/dev/null
            exit 1
        fi

        # Give nginx a moment to refresh DNS (resolver valid=5s) so live
        # traffic actually starts hitting the new IP before we drop the old.
        sleep 6

        log "  stopping old app container ($OLD_APP)..."
        docker stop "$OLD_APP" >/dev/null
        docker rm "$OLD_APP" >/dev/null
    fi

    log "  scaling app back to 1..."
    docker compose up -d --no-deps --no-recreate --scale app=1 app 2>&1 | tee -a "$LOG_FILE"
else
    log "  no running app container, starting fresh..."
    docker compose up -d --no-deps app 2>&1 | tee -a "$LOG_FILE"
fi

# Worker + scheduler in-place restart (acceptable: tasks queue in broker).
# --remove-orphans: clean up containers from services no longer in the
# active compose set (e.g. reverse-proxy behind a profile we don't activate).
log "Restarting worker + scheduler..."
docker compose up -d --no-deps --remove-orphans worker scheduler 2>&1 | tee -a "$LOG_FILE"

# ── Step 6: Wait for app + scheduler to be healthy ───────────────────────────
wait_healthy app 90
wait_healthy scheduler 60

# ── Step 7: Decide how to handle nginx ───────────────────────────────────────
# Image-change detection: compare the image that the running nginx
# container was launched from (NGINX_IMAGE_BEFORE) against the latest
# tagged 'overfast-api-nginx:latest' (which is what compose build just
# produced). 'docker compose images nginx' returns the running
# container's image, so we use 'docker image inspect' on the tag for
# the freshly built one.
NGINX_IMAGE_AFTER=$(docker image inspect overfast-api-nginx --format '{{.Id}}' 2>/dev/null || true)

log "  Nginx image before: ${NGINX_IMAGE_BEFORE:-<none>}"
log "  Nginx image after : ${NGINX_IMAGE_AFTER:-<none>}"

if [ -z "$NGINX_IMAGE_BEFORE" ]; then
    log "nginx was not running. Starting nginx..."
    docker compose up -d --no-deps nginx 2>&1 | tee -a "$LOG_FILE"
elif [ -n "$NGINX_IMAGE_AFTER" ] && [ "$NGINX_IMAGE_BEFORE" != "$NGINX_IMAGE_AFTER" ]; then
    log "nginx image changed. Recreating nginx container..."
    docker compose up -d --no-deps nginx 2>&1 | tee -a "$LOG_FILE"
else
    log "nginx image unchanged. Reloading nginx config in-place..."
    docker compose exec -T nginx nginx -s reload 2>&1 | tee -a "$LOG_FILE"
fi

# ── Step 8: Final health assertion ───────────────────────────────────────────
log "Verifying all containers are healthy..."
sleep 5
if docker compose ps | grep -E "unhealthy|Exit [^0]"; then
    log "ERROR: One or more containers are unhealthy after deploy!"
    docker compose ps 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

log "Deployment completed successfully!"
docker compose ps 2>&1 | tee -a "$LOG_FILE"
