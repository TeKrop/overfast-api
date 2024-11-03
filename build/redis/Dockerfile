ARG REDIS_VERSION=7

FROM redis:${REDIS_VERSION}-alpine

WORKDIR /redis

COPY init.sh ./

RUN chmod +x init.sh