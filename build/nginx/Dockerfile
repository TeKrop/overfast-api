# Build arguments
ARG OPENRESTY_VERSION=1.27.1.1-0

# Use the OpenResty Alpine base image
FROM openresty/openresty:${OPENRESTY_VERSION}-alpine-fat

# Environment variables
ARG OPENRESTY_VERSION
ENV OPENRESTY_VERSION=${OPENRESTY_VERSION}

# For envsubst command in entrypoint
RUN apk add gettext git zlib-dev

# Install zlib
RUN luarocks install lua-zlib

# Copy Nginx configuration file
COPY overfast-api.conf.template /etc/nginx/conf.d/default.conf.template

# Copy Lua scripts
COPY redis_handler.lua.template /usr/local/openresty/lualib/redis_handler.lua.template

# Add an entrypoint script (optional)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh