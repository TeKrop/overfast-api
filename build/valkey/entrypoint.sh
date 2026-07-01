#!/bin/sh

# vm.overcommit_memory is a host-wide (non-namespaced) kernel setting: a container
# cannot change it without running --privileged, which we don't want to grant.
# If it's 0 on the host, background save may fail under low memory conditions.
# Set it on the HOST (not in this container) with:
#   echo 'vm.overcommit_memory = 1' >> /etc/sysctl.conf && sysctl -p
if [ "$(cat /proc/sys/vm/overcommit_memory 2>/dev/null)" != "1" ]; then
    echo ">>> WARNING: host vm.overcommit_memory is not 1; background save may fail under low memory. See entrypoint.sh for the host-side fix." >&2
fi

# Determine how many CPU cores to use for Valkey
CORES=$(nproc)
THREADS=$((CORES > 1 ? CORES - 1 : 1))
echo ">>> Detected $CORES cores, using $THREADS IO threads for Valkey"

# Start valkey server by letting one CPU core available
# volatile-lru: only evict keys with TTL set (protects permanent unknown-player:status keys)
# RDB persistence: save snapshot if at least 1 key changed in the last hour
valkey-server \
    --io-threads $THREADS \
    --maxmemory ${VALKEY_MEMORY_LIMIT} \
    --maxmemory-policy volatile-lru \
    --dir /data \
    --save "3600 1"