FROM python:3.10-alpine

# Environment variables
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.0.0

# Install required system packages and install poetry
RUN apk add build-base && \
  apk add libffi-dev && \
  pip install poetry==1.0.0

# Copy only requirements (caching in Docker layer)
WORKDIR /code
COPY poetry.lock pyproject.toml app-start.sh favicon.png /code/

# Install dependencies
RUN poetry config virtualenvs.create false && \
	poetry install --no-dev --no-interaction --no-ansi

# Copy the code
COPY ./overfastapi /code/overfastapi

# Configure the command
CMD ["sh", "/code/app-start.sh"]
