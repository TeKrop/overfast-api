# Build arguments
ARG NGINX_VERSION=1.27.2
ARG NGX_HTTP_REDIS_VERSION=0.3.9

FROM nginx:${NGINX_VERSION}-alpine

# Environment variables
ARG NGINX_VERSION
ENV NGINX_VERSION=${NGINX_VERSION}
ARG NGX_HTTP_REDIS_VERSION
ENV NGX_HTTP_REDIS_VERSION=${NGX_HTTP_REDIS_VERSION}

# Download nginx and ngx_http_redis sources
RUN wget https://nginx.org/download/nginx-$NGINX_VERSION.tar.gz && \
  tar -xzvf nginx-$NGINX_VERSION.tar.gz && \
  wget https://github.com/TeKrop/ngx_http_redis/archive/refs/tags/v$NGX_HTTP_REDIS_VERSION.tar.gz && \
  tar -xzvf v$NGX_HTTP_REDIS_VERSION.tar.gz

# Download build dependencies
RUN apk add build-base linux-headers pcre-dev openssl-dev zlib-dev

# Configure nginx with ngx_http_redis module. We must use the same configuration
# settings than the ones used in nginx compilation. We then only build the
# modules, and copy the resulting ngx_http_redis_module.so into nginx modules directory
RUN cd nginx-$NGINX_VERSION && \
  nginx_configure_args=$(nginx -V 2>&1 | grep 'configure arguments:' | sed -e "s/configure arguments://") && \
  echo "./configure $nginx_configure_args --add-dynamic-module=../ngx_http_redis-$NGX_HTTP_REDIS_VERSION" > configure.sh && \
  chmod +x configure.sh && \
  ./configure.sh && \
  make modules && \
  cp objs/ngx_http_redis_module.so /usr/lib/nginx/modules/ngx_http_redis_module.so

# Copy specific configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY overfast-api.conf /etc/nginx/conf.d/default.conf

# Clean everything
RUN rm -rf nginx-$NGINX_VERSION* && \
  rm -rf ngx_http_redis-$NGX_HTTP_REDIS_VERSION*