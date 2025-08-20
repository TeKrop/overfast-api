#!/bin/sh

# Backup unlock-data-cache every hour
valkey-cli --raw -D "" DUMP unlock-data-cache > /data/unlock-data-cache.dump