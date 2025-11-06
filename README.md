# Python-TG

Python Telegram Bot Project

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd python-tg
```

2. Create virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Copy environment variables:
```bash
copy .env.example .env  # Windows
# or
cp .env.example .env  # Linux/Mac
```

5. Edit `.env` file with your configuration

## 📁 Project Structure

```
python-tg/
├── src/                # Main source code
│   ├── api/            # API endpoints/routes
│   ├── core/           # Core business logic
│   ├── models/         # Data models
│   ├── services/       # Service layer
│   ├── repositories/   # Data access layer
│   └── utils/          # Utility functions
├── tests/              # Test files
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docs/               # Documentation
│   ├── tech_task/      # Technical specifications
│   └── examples/       # Code examples
├── docker/             # Docker configs
├── config/             # Configuration files
├── scripts/            # Utility scripts
└── .github/            # GitHub configs
```

## 🧪 Development

### Using Development Scripts

We provide helper scripts for common development tasks:

**Windows (PowerShell):**
```powershell
.\scripts\dev.ps1 <command>
```

**Linux/Mac:**
```bash
chmod +x scripts/dev.sh
./scripts/dev.sh <command>
```

**Available commands:**
- `test` - Run tests
- `test-cov` - Run tests with coverage report
- `format` - Format code with black and isort
- `lint` - Run flake8 linter
- `type-check` - Run mypy type checker
- `audit` - Check dependencies for vulnerabilities
- `check-all` - Run all checks (format, lint, type-check, test, audit)
- `clean` - Clean up cache files and build artifacts
- `install` - Install development dependencies
- `help` - Show help message

### Manual Commands

If you prefer to run commands manually:

**Run Tests:**
```bash
pytest
# With coverage
pytest --cov=src --cov-report=html
```

**Format Code:**
```bash
black .
isort .
```

**Type Checking:**
```bash
mypy src/
```

**Linting:**
```bash
flake8 src/
```

**Security Audit:**
```bash
# On Windows, set UTF-8 first
$env:PYTHONUTF8=1; pip-audit

# On Linux/Mac
pip-audit
```

## 📝 License

MIT License
