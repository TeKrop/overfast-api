# Build arguments
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.3.3

# Create a temporary stage to pull the uv binary
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-stage

# Main stage
FROM python:${PYTHON_VERSION}-alpine AS main

# Copy the uv binary from the temporary stage to the main stage
COPY --from=uv-stage /uv /bin/uv

# Copy only requirements (caching in Docker layer)
COPY pyproject.toml uv.lock /code/

# Sync the project into a new environment (no dev dependencies)
WORKDIR /code
RUN uv sync --frozen --no-cache --no-dev

# Copy code and static folders
COPY ./app /code/app
COPY ./static /code/static

# Copy crontabs file and make it executable
COPY ./build/overfast-crontab /etc/crontabs/root
RUN chmod +x /etc/crontabs/root

# For dev image, copy the tests and install necessary dependencies
FROM main as dev
RUN uv sync --frozen --no-cache
COPY ./tests /code/tests