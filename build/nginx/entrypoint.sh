#!/bin/sh

# Fail fast on errors and unset variables; enable pipefail where supported
set -eu
set -o pipefail 2>/dev/null || true

# Set defaults for nginx tuning variables if not provided
: "${NGINX_WORKER_PROCESSES:=0}"
: "${NGINX_WORKER_CONNECTIONS:=1024}"
: "${NGINX_MULTI_ACCEPT:=true}"

# Set defaults for rate limiting variables if not provided
: "${RETRY_AFTER_HEADER:=Retry-After}"
: "${UNKNOWN_PLAYER_COOLDOWN_KEY_PREFIX:=unknown-player:cooldown}"
: "${UNKNOWN_PLAYERS_CACHE_ENABLED:=true}"

# Convert NGINX_WORKER_PROCESSES: 0 → "auto" (nginx auto-detect syntax)
if [ "$NGINX_WORKER_PROCESSES" = "0" ]; then
  NGINX_WORKER_PROCESSES_VALUE="auto"
else
  NGINX_WORKER_PROCESSES_VALUE="$NGINX_WORKER_PROCESSES"
fi

export NGINX_WORKER_PROCESSES_VALUE

# Convert NGINX_MULTI_ACCEPT boolean to nginx syntax (on/off)
if [ "$NGINX_MULTI_ACCEPT" = "true" ] || [ "$NGINX_MULTI_ACCEPT" = "True" ] || [ "$NGINX_MULTI_ACCEPT" = "1" ]; then
  NGINX_MULTI_ACCEPT_VALUE="on"
else
  NGINX_MULTI_ACCEPT_VALUE="off"
fi

export NGINX_MULTI_ACCEPT_VALUE

# Build Prometheus config conditionally by reading template files
if [ "$PROMETHEUS_ENABLED" = "true" ]; then
  PROMETHEUS_LUA_SHARED_DICT=$(cat /etc/nginx/prometheus-templates/prometheus_shared_dict.conf)
  PROMETHEUS_INIT_WORKER=$(cat /etc/nginx/prometheus-templates/prometheus_init_worker.conf)
  PROMETHEUS_LOG_BY_LUA=$(cat /etc/nginx/prometheus-templates/prometheus_log.conf)
  PROMETHEUS_METRICS_SERVER=$(cat /etc/nginx/prometheus-templates/prometheus_metrics_server.conf)
else
  PROMETHEUS_LUA_SHARED_DICT=''
  PROMETHEUS_INIT_WORKER=''
  PROMETHEUS_LOG_BY_LUA=''
  PROMETHEUS_METRICS_SERVER=''
fi

export PROMETHEUS_LUA_SHARED_DICT
export PROMETHEUS_INIT_WORKER
export PROMETHEUS_LOG_BY_LUA
export PROMETHEUS_METRICS_SERVER

# Generate main nginx.conf from template
envsubst '${NGINX_WORKER_PROCESSES_VALUE} ${NGINX_WORKER_CONNECTIONS} ${NGINX_MULTI_ACCEPT_VALUE}' < /etc/nginx/nginx.conf.template > /usr/local/openresty/nginx/conf/nginx.conf

# Replace placeholders and generate config and lua script from templates
envsubst '${RATE_LIMIT_PER_SECOND_PER_IP} ${RATE_LIMIT_PER_IP_BURST} ${MAX_CONNECTIONS_PER_IP} ${RETRY_AFTER_HEADER} ${PROMETHEUS_LUA_SHARED_DICT} ${PROMETHEUS_INIT_WORKER} ${PROMETHEUS_LOG_BY_LUA} ${PROMETHEUS_METRICS_SERVER}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
envsubst '${VALKEY_HOST} ${VALKEY_PORT} ${CACHE_TTL_HEADER} ${RETRY_AFTER_HEADER} ${UNKNOWN_PLAYER_COOLDOWN_KEY_PREFIX} ${UNKNOWN_PLAYERS_CACHE_ENABLED}' < /usr/local/openresty/lualib/valkey_handler.lua.template > /usr/local/openresty/lualib/valkey_handler.lua

# Check OpenResty config before starting
openresty -t

# Start OpenResty
openresty -g "daemon off;"