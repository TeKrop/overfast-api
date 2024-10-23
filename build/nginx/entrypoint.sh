#!/bin/sh

# Replace placeholders and generate config from template
envsubst '${RATE_LIMIT_PER_SECOND_PER_IP} ${RATE_LIMIT_PER_IP_BURST} ${MAX_CONNECTIONS_PER_IP}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Launch nginx
nginx -g 'daemon off;'