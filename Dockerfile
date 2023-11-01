FROM python:3.12-alpine

# Environment variables
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.6.1

# Install required system packages and install poetry
RUN apk add build-base && \
  apk add libffi-dev && \
  pip install poetry==1.6.1

# Copy only requirements (caching in Docker layer)
WORKDIR /code
COPY pyproject.toml scripts/app-start.sh /code/

# Install dependencies
RUN poetry config virtualenvs.create false && \
	poetry install --only main --no-interaction --no-ansi

# Copy code and static folders
COPY ./app /code/app
COPY ./static /code/static

# Configure the command
CMD ["sh", "/code/app-start.sh"]
