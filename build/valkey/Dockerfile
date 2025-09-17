ARG VALKEY_VERSION=8

FROM valkey/valkey:${VALKEY_VERSION}-alpine

WORKDIR /valkey

COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh