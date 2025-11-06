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
        pip install -r requirements-dev.txt
        ;;
    help)
        cat << EOF

Development Script Commands
============================

test         - Run tests
test-cov     - Run tests with coverage report
format       - Format code with black and isort
lint         - Run flake8 linter
type-check   - Run mypy type checker
audit        - Check dependencies for vulnerabilities
check-all    - Run all checks (format, lint, type-check, test, audit)
clean        - Clean up cache files and build artifacts
install      - Install development dependencies
help         - Show this help message

Usage: ./scripts/dev.sh <command>

Examples:
  ./scripts/dev.sh test
  ./scripts/dev.sh format
  ./scripts/dev.sh check-all

EOF
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run './scripts/dev.sh help' for available commands"
        exit 1
        ;;
esac
