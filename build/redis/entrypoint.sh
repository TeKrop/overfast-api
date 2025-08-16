#!/bin/sh

# WARNING overcommit_memory is set to 0! Background save may fail under low memory condition.
# To fix this issue add 'vm.overcommit_memory = 1' to /etc/sysctl.conf and then reboot
# or run the command 'sysctl vm.overcommit_memory=1' for this to take effect.
# The overcommit_memory has 3 options.
# 0, the system kernel check if there is enough memory to be allocated to the process or not, 
# if not enough, it will return errors to the process.
# 1, the system kernel is allowed to allocate the whole memory to the process
# no matter what the status of memory is.
# 2, the system kernel is allowed to allocate a memory whose size could be bigger than
# the sum of the size of physical memory and the size of exchange workspace to the process.
sysctl vm.overcommit_memory=1

# Start cron in the background
crond

# Start the restore script in the background
/usr/local/bin/redis-unlock-restore.sh &

# Start redis server
redis-server \
    --maxmemory ${REDIS_MEMORY_LIMIT} \
    --maxmemory-policy allkeys-lru \
    --save ""