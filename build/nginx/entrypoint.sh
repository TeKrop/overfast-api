#!/bin/sh

# Replace placeholders and generate config and lua script from templates
envsubst '${RATE_LIMIT_PER_SECOND_PER_IP} ${RATE_LIMIT_PER_IP_BURST} ${MAX_CONNECTIONS_PER_IP} ${RETRY_AFTER_HEADER}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
envsubst '${REDIS_HOST} ${REDIS_PORT} ${CACHE_TTL_HEADER}' < /usr/local/openresty/lualib/redis_handler.lua.template > /usr/local/openresty/lualib/redis_handler.lua

# Check OpenResty config before starting
openresty -t

# Start OpenResty
openresty -g "daemon off;"