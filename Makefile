# Default target
.DEFAULT_GOAL := help

# Help message
help:
	@echo "============================================================================="
	@echo " OverFast API Makefile Help"
	@echo "============================================================================="
	@echo "Available targets:"
	@echo ""
	@echo "  make install"
	@echo "      Install dependencies."
	@echo ""
	@echo "  make run"
	@echo "      Run OverFastAPI application."
	@echo ""
	@echo "  make test [TARGET=path/to/tests] [COVERAGE=true]"
	@echo "      Run tests with optional coverage calculation and target specification."
	@echo ""
	@echo "  make lint"
	@echo "      Run linter."
	@echo ""
	@echo "  make format"
	@echo "      Run formatter."
	@echo ""
	@echo "  make docker-up"
	@echo "      Build and run the project using Docker Compose."
	@echo ""
	@echo "  make clean"
	@echo "      Remove generated files."
	@echo "============================================================================="

# Install dependencies
install:
	@echo "Installing dependencies..."
	poetry lock --no-update
	poetry install

# Run OverFastAPI application
run:
	@echo "Launching OverFastAPI..."
	uvicorn app.main:app --reload

# Run tests with coverage (optional)
test:
ifdef COVERAGE
	@echo "Running tests with coverage..."
	python -m pytest --cov app --cov-report html -n auto $(TARGET)
else
	@echo "Running tests..."
	python -m pytest -n auto $(TARGET)
endif

# Run linter
lint:
	@echo "Running linter..."
	ruff check --fix --exit-non-zero-on-fix

# Run formatter
format:
	@echo "Running formatter..."
	ruff format

# Build and run the project using Docker Compose
docker-up:
	@echo "Building and running the project using Docker Compose..."
	docker compose up --build -d

# Clean up generated files
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ .pytest_cache htmlcov

.PHONY: help install run test lint format docker-up clean