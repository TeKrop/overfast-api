#!/bin/sh

DUMP_FILE="/data/unlock-data-cache.dump"

# Wait for Valkey server to be up by pinging it repeatedly
until valkey-cli PING | grep -q "PONG"; do
    echo "[restore] Waiting for Valkey server to start..."
    sleep 1
done

if [ -s "$DUMP_FILE" ]; then
    echo "[restore] Restoring unlock-data-cache from dump..."
    valkey-cli DEL unlock-data-cache
    cat "$DUMP_FILE" | valkey-cli -x RESTORE unlock-data-cache 0
else
    echo "[restore] No unlock-data-cache.dump file found or file is empty, skipping restore."
fi