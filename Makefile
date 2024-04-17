# Default target
.DEFAULT_GOAL := help

# Colors
YELLOW := \033[1;33m
GREEN := \033[1;32m
CYAN := \033[1;36m
RESET := \033[0m

# Aliases
DOCKER_RUN := docker compose run \
	--volume ${PWD}/app:/code/app \
	--volume ${PWD}/tests:/code/tests \
	--volume ${PWD}/htmlcov:/code/htmlcov \
	--volume ${PWD}/logs:/code/logs \
	--publish 8000:8000 \
	--rm \
	app

help:
	@echo "Usage: make <command>"
	@echo ""
	@echo "${CYAN}Commands:${RESET}"
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "build" "Build project images (dev mode)."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "start" "Run OverFastAPI application (dev mode)."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "lint" "Run linter."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "format" "Run formatter."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "shell" "Access an interactive shell inside the app container"
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "exec" "Execute a given COMMAND inside the app container"
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "test" "Run tests. PYTEST_ARGS can be specified."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "up" "Build & run OverFastAPI application (production mode)."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "down" "Stop the app and remove containers."
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "clean" "Clean up Docker environment"
	@printf "  ${GREEN}%-10s${RESET} : ${YELLOW}%s${RESET}\n" "help" "Show this help message"

# Build project images
build:
	@echo "Building OverFastAPI (dev mode)..."
	BUILD_TARGET="dev" docker compose build

# Run OverFastAPI application (dev mode)
start:
	@echo "Launching OverFastAPI (dev mode)..."
	$(DOCKER_RUN) uvicorn app.main:app --reload --host 0.0.0.0

# Run linter
lint:
	@echo "Running linter..."
	$(DOCKER_RUN) ruff check --fix --exit-non-zero-on-fix

# Run formatter
format:
	@echo "Running formatter..."
	$(DOCKER_RUN) ruff format

# Open a shell on the app container
shell:
	@echo "Running shell on app container..."
	$(DOCKER_RUN) /bin/sh

# Execute a command on the app container
exec:
	@echo "Running shell on app container..."
	$(DOCKER_RUN) $(COMMAND)

# Run tests (no coverage calculation if a target is specified)
test: build
ifdef PYTEST_ARGS
	@echo "Running tests on $(PYTEST_ARGS)..."
	$(DOCKER_RUN) python -m pytest $(PYTEST_ARGS)
else
	@echo "Running all tests with coverage..."
	$(DOCKER_RUN) python -m pytest --cov app --cov-report html -n auto
endif

# Run OverFastAPI application (production mode)
up:
	@echo "Building OverFastAPI (production mode)..."
	docker compose build
	@echo "Stopping OverFastAPI and cleaning containers..."
	docker compose down -v --remove-orphans
	@echo "Launching OverFastAPI (production mode)..."
	docker compose up -d

# Remove containers
down:
	@echo "Stopping OverFastAPI and cleaning containers..."
	docker compose down -v --remove-orphans

# Clean Docker environment
clean: down
	@echo "Cleaning Docker environment..."
	docker image prune -af
	docker network prune -f

.PHONY: help build start lint format shell exec test up down clean