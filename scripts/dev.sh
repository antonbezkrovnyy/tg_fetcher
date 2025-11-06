#!/bin/bash
# Development utility script for Linux/Mac
# Run with: ./scripts/dev.sh <command>

set -e

# Set UTF-8 encoding for Python
export PYTHONUTF8=1

COMMAND=${1:-help}

case "$COMMAND" in
    test)
        echo "Running tests..."
        pytest
        ;;
    test-cov)
        echo "Running tests with coverage..."
        pytest --cov=src --cov-report=html --cov-report=term
        ;;
    format)
        echo "Formatting code..."
        black .
        isort .
        ;;
    lint)
        echo "Linting code..."
        flake8 src/
        ;;
    type-check)
        echo "Type checking..."
        mypy src/
        ;;
    audit)
        echo "Checking dependencies for vulnerabilities..."
        pip-audit
        ;;
    check-all)
        echo "Running all checks..."
        echo -e "\n=== Formatting ==="
        black . --check
        isort . --check
        echo -e "\n=== Linting ==="
        flake8 src/
        echo -e "\n=== Type Checking ==="
        mypy src/
        echo -e "\n=== Tests ==="
        pytest --cov=src
        echo -e "\n=== Security Audit ==="
        pip-audit
        ;;
    clean)
        echo "Cleaning up..."
        rm -rf .pytest_cache htmlcov .coverage .mypy_cache
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        echo "Cleanup complete!"
        ;;
    install)
        echo "Installing dependencies..."
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        ;;
    run)
        echo "Running Telegram Fetcher..."
        python -m src
        ;;
    auth)
        echo "Authorizing Telegram session..."
        python scripts/authorize_session.py
        ;;
    docker-build)
        echo "Building Docker image..."
        docker build -t telegram-fetcher:latest .
        ;;
    docker-up)
        echo "Starting Docker services..."
        # Create volumes first
        docker volume create observability-stack_prometheus-data 2>/dev/null || true
        docker volume create observability-stack_loki-data 2>/dev/null || true
        docker volume create observability-stack_grafana-data 2>/dev/null || true
        docker volume create observability-stack_pushgateway-data 2>/dev/null || true
        docker-compose up -d --build
        ;;
    docker-down)
        echo "Stopping Docker services..."
        docker-compose down
        ;;
    docker-logs)
        echo "Showing Docker logs..."
        docker-compose logs -f telegram-fetcher
        ;;
    docker-clean)
        echo "Cleaning Docker resources..."
        docker-compose down -v
        docker system prune -f
        ;;
    setup-env)
        echo "Setting up environment file..."
        if [ -f .env ]; then
            echo ".env already exists!"
        else
            cp .env.example .env
            echo ".env created from .env.example"
            echo "Please edit .env with your Telegram credentials!"
        fi
        ;;
    help)
        cat << EOF

Development Script Commands
============================

Testing & Quality:
  test         - Run tests
  test-cov     - Run tests with coverage report
  format       - Format code with black and isort
  lint         - Run flake8 linter
  type-check   - Run mypy type checker
  audit        - Check dependencies for vulnerabilities
  check-all    - Run all checks (format, lint, type-check, test, audit)

Application:
  run          - Run Telegram Fetcher locally
  auth         - Authorize Telegram session (interactive)
  setup-env    - Create .env from .env.example

Docker:
  docker-build - Build Docker image
  docker-up    - Start all services with docker-compose (creates volumes)
  docker-down  - Stop all Docker services
  docker-logs  - Show fetcher service logs
  docker-clean - Stop services and clean up volumes/images

Maintenance:
  clean        - Clean up cache files and build artifacts
  install      - Install all dependencies (production + dev)
  help         - Show this help message

Usage: ./scripts/dev.sh <command>

Examples:
  ./scripts/dev.sh setup-env     # First time setup
  ./scripts/dev.sh install       # Install dependencies
  ./scripts/dev.sh auth          # Authorize Telegram session
  ./scripts/dev.sh run           # Run locally
  ./scripts/dev.sh docker-up     # Run in Docker with observability
  ./scripts/dev.sh docker-logs   # View logs

EOF
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run './scripts/dev.sh help' for available commands"
        exit 1
        ;;
esac
