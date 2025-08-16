ARG REDIS_VERSION=8

FROM redis:${REDIS_VERSION}-alpine

# Install cron
RUN apk add --no-cache busybox-suid

# Copy backup, restore scripts and crontab file
COPY redis-unlock-backup.sh /usr/local/bin/redis-unlock-backup.sh
COPY redis-unlock-restore.sh /usr/local/bin/redis-unlock-restore.sh
COPY unlock-crontab /etc/crontabs/root

# Make the scripts executable
RUN chmod +x /usr/local/bin/redis-unlock-backup.sh
RUN chmod +x /usr/local/bin/redis-unlock-restore.sh

WORKDIR /redis

COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh