# Build arguments
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.4.5

# Main stage
FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-alpine AS main

# Copy only requirements (caching in Docker layer)
COPY pyproject.toml uv.lock /code/

# Sync the project into a new environment (no dev dependencies)
WORKDIR /code

# Copy code and static folders
COPY ./app /code/app
COPY ./static /code/static

# Install the project
RUN uv sync --frozen --no-cache --no-dev

# Copy crontabs file and make it executable
COPY ./build/overfast-crontab /etc/crontabs/root
RUN chmod +x /etc/crontabs/root

# For dev image, copy the tests and install necessary dependencies
FROM main as dev
RUN uv sync --frozen --no-cache
COPY ./tests /code/tests