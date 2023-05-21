FROM nginx:1.20.2-alpine

# Copy specific configuration files and libraries
COPY nginx.conf /etc/nginx/nginx.conf
COPY ngx_http_redis_module.so /usr/lib/nginx/modules/ngx_http_redis_module.so
COPY overfast-api.conf /etc/nginx/conf.d/default.conf