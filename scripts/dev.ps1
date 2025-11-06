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
        pip install -r requirements-dev.txt
    }
    "help" {
        Write-Host @"

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

Usage: .\scripts\dev.ps1 <command>

Examples:
  .\scripts\dev.ps1 test
  .\scripts\dev.ps1 format
  .\scripts\dev.ps1 check-all

"@ -ForegroundColor Cyan
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run '.\scripts\dev.ps1 help' for available commands" -ForegroundColor Yellow
    }
}
