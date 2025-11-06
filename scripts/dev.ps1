# Development utility script for Windows
# Run with: .\scripts\dev.ps1 <command>

param(
    [Parameter(Position=0, Mandatory=$false)]
    [string]$Command = "help"
)

# Set UTF-8 encoding for Python
$env:PYTHONUTF8 = 1

switch ($Command) {
    "test" {
        Write-Host "Running tests..." -ForegroundColor Green
        pytest
    }
    "test-cov" {
        Write-Host "Running tests with coverage..." -ForegroundColor Green
        pytest --cov=src --cov-report=html --cov-report=term
    }
    "format" {
        Write-Host "Formatting code..." -ForegroundColor Green
        black .
        isort .
    }
    "lint" {
        Write-Host "Linting code..." -ForegroundColor Green
        flake8 src/
    }
    "type-check" {
        Write-Host "Type checking..." -ForegroundColor Green
        mypy src/
    }
    "audit" {
        Write-Host "Checking dependencies for vulnerabilities..." -ForegroundColor Green
        pip-audit
    }
    "check-all" {
        Write-Host "Running all checks..." -ForegroundColor Green
        Write-Host "`n=== Formatting ===" -ForegroundColor Cyan
        black . --check
        isort . --check
        Write-Host "`n=== Linting ===" -ForegroundColor Cyan
        flake8 src/
        Write-Host "`n=== Type Checking ===" -ForegroundColor Cyan
        mypy src/
        Write-Host "`n=== Tests ===" -ForegroundColor Cyan
        pytest --cov=src
        Write-Host "`n=== Security Audit ===" -ForegroundColor Cyan
        pip-audit
    }
    "clean" {
        Write-Host "Cleaning up..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue htmlcov
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .coverage
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .mypy_cache
        Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
        Write-Host "Cleanup complete!" -ForegroundColor Green
    }
    "install" {
        Write-Host "Installing dependencies..." -ForegroundColor Green
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    }
    "run" {
        Write-Host "Running Telegram Fetcher..." -ForegroundColor Green
        python -m src
    }
    "docker-build" {
        Write-Host "Building Docker image..." -ForegroundColor Green
        docker build -t telegram-fetcher:latest .
    }
    "docker-up" {
        Write-Host "Starting Docker services..." -ForegroundColor Green
        # Create volumes first
        docker volume create observability-stack_prometheus-data -ErrorAction SilentlyContinue
        docker volume create observability-stack_loki-data -ErrorAction SilentlyContinue
        docker volume create observability-stack_grafana-data -ErrorAction SilentlyContinue
        docker volume create observability-stack_pushgateway-data -ErrorAction SilentlyContinue
        docker-compose up -d --build
    }
    "docker-down" {
        Write-Host "Stopping Docker services..." -ForegroundColor Yellow
        docker-compose down
    }
    "docker-logs" {
        Write-Host "Showing Docker logs..." -ForegroundColor Green
        docker-compose logs -f telegram-fetcher
    }
    "docker-clean" {
        Write-Host "Cleaning Docker resources..." -ForegroundColor Yellow
        docker-compose down -v
        docker system prune -f
    }
    "setup-env" {
        Write-Host "Setting up environment file..." -ForegroundColor Green
        if (Test-Path .env) {
            Write-Host ".env already exists!" -ForegroundColor Yellow
        } else {
            Copy-Item .env.example .env
            Write-Host ".env created from .env.example" -ForegroundColor Green
            Write-Host "Please edit .env with your Telegram credentials!" -ForegroundColor Cyan
        }
    }
    "help" {
        Write-Host @"

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

Usage: .\scripts\dev.ps1 <command>

Examples:
  .\scripts\dev.ps1 setup-env     # First time setup
  .\scripts\dev.ps1 install       # Install dependencies
  .\scripts\dev.ps1 run           # Run locally
  .\scripts\dev.ps1 docker-up     # Run in Docker with observability
  .\scripts\dev.ps1 docker-logs   # View logs

"@ -ForegroundColor Cyan
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run '.\scripts\dev.ps1 help' for available commands" -ForegroundColor Yellow
    }
}
