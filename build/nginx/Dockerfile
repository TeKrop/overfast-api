# Build arguments
ARG OPENRESTY_VERSION=1.27.1.2-3

# Use the OpenResty Alpine base image
FROM openresty/openresty:${OPENRESTY_VERSION}-alpine-fat

# Environment variables
ARG OPENRESTY_VERSION
ENV OPENRESTY_VERSION=${OPENRESTY_VERSION}

# For envsubst command in entrypoint
RUN apk add --no-cache gettext git zstd-dev

# Install lua-zstd and lua-resty-prometheus
RUN luarocks install lua-zstd && \
    luarocks install nginx-lua-prometheus

# Copy main Nginx configuration template
COPY nginx.conf.template /etc/nginx/nginx.conf.template

# Copy Nginx configuration files
COPY overfast-api.conf.template /etc/nginx/conf.d/default.conf.template
# Copy Prometheus templates to a separate directory (not conf.d to avoid auto-loading)
COPY prometheus_shared_dict.conf /etc/nginx/prometheus-templates/prometheus_shared_dict.conf
COPY prometheus_init_worker.conf /etc/nginx/prometheus-templates/prometheus_init_worker.conf
COPY prometheus_log.conf /etc/nginx/prometheus-templates/prometheus_log.conf
COPY prometheus_metrics_server.conf /etc/nginx/prometheus-templates/prometheus_metrics_server.conf

# Copy Lua scripts
COPY valkey_handler.lua.template /usr/local/openresty/lualib/valkey_handler.lua.template

# Add an entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh