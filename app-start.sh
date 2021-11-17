#!/bin/sh

# Start crond
crond -f &

# Start python server
cd /code
uvicorn overfastapi.main:app --host "0.0.0.0" --port 8080 --proxy-headers
