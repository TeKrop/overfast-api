# Aliases
docker_compose := "docker compose"
docker_run := docker_compose + " run \
    --volume ${PWD}/app:/code/app \
    --volume ${PWD}/tests:/code/tests \
    --volume ${PWD}/htmlcov:/code/htmlcov \
    --volume ${PWD}/logs:/code/logs \
    --volume ${PWD}/static:/code/static \
    --publish 8000:8000 \
    --rm \
    app"

# print recipe names and comments as help
help:
    @just --list

# build project images
build:
    @echo "Building OverFastAPI (dev mode)..."
    BUILD_TARGET="dev" {{docker_compose}} build

# run OverFastAPI application (dev mode)
start:
    @echo "Launching OverFastAPI in dev mode with autoreload..."
    {{docker_run}} uv run fastapi dev app/main.py --host 0.0.0.0

# run OverFastAPI application (testing mode)
start_testing:
    @echo "Launching OverFastAPI in testing mode with reverse proxy..."
    {{docker_compose}} --profile testing up -d

# run type checker
check checker_args="":
    @echo {{ if checker_args != "" { "Running type checker on " + checker_args + "..." } else { "Running type checker..." } }}
    {{ if checker_args != "" { "uvx ty check " + checker_args } else { "uvx ty check" } }}

# run linter
lint:
    @echo "Running linter..."
    uvx ruff check --fix --exit-non-zero-on-fix

# run formatter
format:
    @echo "Running formatter..."
    uvx ruff format

# access an interactive shell inside the app container
shell:
    @echo "Running shell on app container..."
    {{docker_run}} /bin/sh

# execute a given command inside the app container
exec command="":
    @echo "Running command on app container..."
    {{docker_run}} {{command}}

# run tests, pytest_args can be specified
test pytest_args="":
    @echo {{ if pytest_args != "" { "Running tests on " + pytest_args + "..." } else { "Running all tests with coverage..." } }}
    {{docker_run}} {{ if pytest_args != "" { "uv run python -m pytest " + pytest_args } else { "uv run python -m pytest --cov app/ --cov-report html -n auto tests/" } }}

# build & run OverFastAPI application (production mode)
up:
    @echo "Building OverFastAPI (production mode)..."
    {{docker_compose}} build
    @echo "Stopping OverFastAPI and cleaning containers..."
    {{docker_compose}} down -v --remove-orphans
    @echo "Launching OverFastAPI (production mode)..."
    {{docker_compose}} up -d

# stop the app and remove containers
down:
    @echo "Stopping OverFastAPI and cleaning containers..."
    {{docker_compose}} --profile "*" down -v --remove-orphans

# clean up Docker environment
clean: down
    @echo "Cleaning Docker environment..."
    docker image prune -af
    docker network prune -f

# update lock file
lock:
    uv lock

# update test fixtures (heroes, players, etc.)
update_test_fixtures params="":
    {{docker_run}} uv run python -m tests.update_test_fixtures {{params}}