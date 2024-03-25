FROM python:3.12-alpine AS main

WORKDIR /code

# Environment variables
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.8.2

# Install required system packages and install poetry
RUN apk add build-base && \
  apk add libffi-dev && \
  pip install poetry==1.8.2

# Copy only requirements (caching in Docker layer)
COPY pyproject.toml /code/

# Install dependencies
RUN poetry config virtualenvs.create false && \
	poetry install --only main --no-interaction --no-ansi

# Copy code and static folders
COPY ./app /code/app
COPY ./static /code/static

# Copy crontabs file and make it executable
COPY ./build/overfast-crontab /etc/crontabs/root
RUN chmod +x /etc/crontabs/root

# For dev image, copy the tests and install necessary dependencies
FROM main as dev
RUN poetry install --only dev --no-interaction --no-ansi
COPY ./tests /code/tests
