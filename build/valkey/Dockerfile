ARG VALKEY_VERSION=8

FROM valkey/valkey:${VALKEY_VERSION}-alpine

# Install cron
RUN apk add --no-cache busybox-suid

# Copy backup, restore scripts and crontab file
COPY valkey-unlock-backup.sh /usr/local/bin/valkey-unlock-backup.sh
COPY valkey-unlock-restore.sh /usr/local/bin/valkey-unlock-restore.sh
COPY unlock-crontab /etc/crontabs/root

# Make the scripts executable
RUN chmod +x /usr/local/bin/valkey-unlock-backup.sh
RUN chmod +x /usr/local/bin/valkey-unlock-restore.sh

WORKDIR /valkey

COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh