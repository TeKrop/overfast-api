#!/bin/sh

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

# Replace placeholders and generate config and lua script from templates
envsubst '${RATE_LIMIT_PER_SECOND_PER_IP} ${RATE_LIMIT_PER_IP_BURST} ${MAX_CONNECTIONS_PER_IP} ${RETRY_AFTER_HEADER} ${PROMETHEUS_LUA_SHARED_DICT} ${PROMETHEUS_INIT_WORKER} ${PROMETHEUS_LOG_BY_LUA} ${PROMETHEUS_METRICS_SERVER}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
envsubst '${VALKEY_HOST} ${VALKEY_PORT} ${CACHE_TTL_HEADER} ${PROMETHEUS_ENABLED}' < /usr/local/openresty/lualib/valkey_handler.lua.template > /usr/local/openresty/lualib/valkey_handler.lua

# Check OpenResty config before starting
openresty -t

# Start OpenResty
openresty -g "daemon off;"