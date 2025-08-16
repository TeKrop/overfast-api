#!/bin/sh

# Backup unlock-data-cache every hour
redis-cli --raw -D "" DUMP unlock-data-cache > /data/unlock-data-cache.dump