# Telegram Messages Fetcher Service

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellowgreen.svg)](https://flake8.pycqa.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

Production-ready service for fetching messages from Telegram channels and chats with complete observability stack integration.

**Author:** [Anton Bezkrovnyy](https://github.com/antonbezkrovnyy)

## ✨ Features

- 📥 **Message Fetching**: Collect messages from Telegram channels and chats
- 💬 **Reactions & Comments**: Extract emoji reactions and discussion thread comments
- 📊 **Multiple Fetch Modes**: yesterday, full, incremental, continuous, date, range
- 🔄 **Progress Tracking**: Resume from where you left off
- 📈 **Full Observability**: Integrated with Prometheus, Loki, and Grafana
- 🔒 **Type-Safe**: Built with Pydantic v2 for validation
- 🐳 **Docker-Ready**: Multi-stage build with observability stack
- 💾 **Versioned Schema**: JSON storage with schema versioning

## 🚀 Quick Start

### Using Scripts (Recommended)

**Windows:**
```powershell
# One-command setup and run
.\scripts\quickstart.ps1
```

**Linux/Mac:**
```bash
# One-command setup and run
chmod +x scripts/*.sh
./scripts/quickstart.sh
```

This will:
1. Create `.env` from template
2. Create Docker volumes
3. Build and start all services
4. Show access URLs

### Manual Setup

1. **Setup environment:**
```bash
# Windows
.\scripts\dev.ps1 setup-env

# Linux/Mac
./scripts/dev.sh setup-env
```

2. **Edit `.env` with your Telegram credentials:**
```env
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=your_hash_here
TELEGRAM_PHONE=+1234567890
TELEGRAM_CHATS=@channel1,@channel2
```

3. **Run with Docker:**
```bash
# Windows
.\scripts\dev.ps1 docker-up

# Linux/Mac
./scripts/dev.sh docker-up
```

## 📊 Access Services

Once running:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100
- **Pushgateway**: http://localhost:9091

## 🛠️ Development Scripts

### Windows (PowerShell)

```powershell
# Setup and run
.\scripts\dev.ps1 setup-env     # Create .env file
.\scripts\dev.ps1 install       # Install dependencies
.\scripts\dev.ps1 run           # Run locally

# Docker commands
.\scripts\dev.ps1 docker-up     # Start all services
.\scripts\dev.ps1 docker-down   # Stop services
.\scripts\dev.ps1 docker-logs   # View logs
.\scripts\dev.ps1 docker-clean  # Clean up

# Development
.\scripts\dev.ps1 test          # Run tests
.\scripts\dev.ps1 format        # Format code
.\scripts\dev.ps1 check-all     # Run all checks

# Utilities
.\scripts\quickstart.ps1        # Full setup from scratch
.\scripts\status.ps1            # Check system status
```

### Linux/Mac (Bash)

```bash
# Setup and run
./scripts/dev.sh setup-env      # Create .env file
./scripts/dev.sh install        # Install dependencies
./scripts/dev.sh run            # Run locally

# Docker commands
./scripts/dev.sh docker-up      # Start all services
./scripts/dev.sh docker-down    # Stop services
./scripts/dev.sh docker-logs    # View logs
./scripts/dev.sh docker-clean   # Clean up

# Development
./scripts/dev.sh test           # Run tests
./scripts/dev.sh format         # Format code
./scripts/dev.sh check-all      # Run all checks

# Utilities
./scripts/quickstart.sh         # Full setup from scratch
./scripts/status.sh             # Check system status
```

## 📁 Project Structure

```
python-tg/
├── src/
│   ├── core/              # Configuration and core logic
│   ├── models/            # Pydantic data models
│   ├── services/          # Business logic services
│   │   └── strategy/      # Fetch mode strategies
│   ├── repositories/      # Data persistence layer
│   └── observability/     # Logging and metrics
├── infrastructure/
│   └── observability-stack/  # Git submodule
├── scripts/               # Development and deployment scripts
├── docs/                  # Documentation
│   ├── tech_task/         # Technical specifications
│   └── examples/          # Reference implementations
├── data/                  # Fetched messages (JSON)
├── sessions/              # Telegram session files
└── docker-compose.yml     # Full stack deployment
```

## 📝 Configuration

All configuration via environment variables (`.env` file):

### Required
- `TELEGRAM_API_ID` - From https://my.telegram.org/apps
- `TELEGRAM_API_HASH` - From https://my.telegram.org/apps
- `TELEGRAM_PHONE` - International format (+1234567890)
- `TELEGRAM_CHATS` - Comma-separated list (@channel1,@channel2)

### Optional
- `FETCH_MODE` - yesterday (default), full, incremental, continuous, date, range
- `DATA_DIR` - Data storage directory (default: ./data)
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LOG_FORMAT` - json (default) or text
- `LOKI_URL` - Loki endpoint (auto-configured in Docker)
- `PUSHGATEWAY_URL` - Pushgateway endpoint (auto-configured in Docker)

See `.env.example` for full list.

## 📦 Data Format

Messages are stored as JSON with versioned schema:

```json
{
  "version": "1.0",
  "source_info": {
    "id": "@channel",
    "title": "Channel Name",
    "url": "https://t.me/channel",
    "type": "channel"
  },
  "senders": {
    "123456": "User Name"
  },
  "messages": [
    {
      "id": 12345,
      "date": "2025-11-06T10:30:00+00:00",
      "text": "Message text",
      "sender_id": 123456,
      "reactions": [
        {"emoji": "👍", "count": 12}
      ],
      "comments": []
    }
  ]
}
```

## 🧪 Testing

```bash
# Run tests
./scripts/dev.sh test

# With coverage
./scripts/dev.sh test-cov

# Check everything
./scripts/dev.sh check-all
```

## 📖 Documentation

- [Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md)
- [Technical Specification](docs/tech_task/TZ-telegram-fetcher.md)
- [Pre-Implementation Checklist](docs/PRE_IMPLEMENTATION_CHECKLIST.md)
- [Copilot Instructions](.github/copilot-instructions.md)

## 🔍 Monitoring

### View Logs in Grafana

1. Open Grafana: http://localhost:3000
2. Go to Explore
3. Select Loki data source
4. Query: `{service="telegram-fetcher"}`

### View Metrics in Prometheus

1. Open Prometheus: http://localhost:9090
2. Go to Graph
3. Query metrics (e.g., `telegram_messages_fetched_total`)

## 🐛 Troubleshooting

### Check System Status
```bash
# Windows
.\scripts\status.ps1

# Linux/Mac
./scripts/status.sh
```

### View Logs
```bash
docker-compose logs -f telegram-fetcher
```

### Reset Everything
```bash
# Windows
.\scripts\dev.ps1 docker-clean

# Linux/Mac
./scripts/dev.sh docker-clean
```

## 🏗️ Architecture

- **Pydantic v2**: Type-safe configuration and data models
- **Repository Pattern**: Clean data access layer
- **Strategy Pattern**: Pluggable fetch modes
- **Service Layer**: Business logic isolation
- **Observability**: Structured logging with Loki, metrics with Prometheus
- **Docker**: Multi-stage build, minimal production image

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 [Anton Bezkrovnyy](https://github.com/antonbezkrovnyy)

## 🤝 Contributing

[Add contribution guidelines here]
