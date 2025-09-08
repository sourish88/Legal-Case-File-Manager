# Makefile for Legal Case File Manager

.PHONY: help install install-dev setup-db run test lint format clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  setup-db     - Set up database and generate sample data"
	@echo "  run          - Run the application"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting (flake8, mypy)"
	@echo "  format       - Format code (black, isort)"
	@echo "  clean        - Clean up cache files"
	@echo "  pre-commit   - Install pre-commit hooks"

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Set up database and generate sample data
setup-db:
	python scripts/database_setup.py
	python scripts/generate_dummy_data.py --count 50 --clear

# Run the application
run:
	python run.py

# Run tests
test:
	pytest tests/ -v

# Run linting
lint:
	flake8 app/ scripts/ tests/
	mypy app/ --ignore-missing-imports

# Format code
format:
	black app/ scripts/ tests/ run.py
	isort app/ scripts/ tests/ run.py

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Install pre-commit hooks
pre-commit:
	pre-commit install

# Development setup (run this after cloning)
dev-setup: install-dev pre-commit setup-db
	@echo "Development environment setup complete!"
	@echo "Run 'make run' to start the application."
