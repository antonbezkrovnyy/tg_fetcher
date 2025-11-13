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

Note about observability stack
------------------------------

The observability stack (Grafana / Prometheus / Loki / Pushgateway) is managed outside this repository in the workspace-level `infrastructure/` directory. If you use the monorepo/workspace provided here, start the observability services from that folder (see `infrastructure/` in the workspace root). This repository's `docker-compose.yml` expects those services to be available on the `tg-infrastructure` Docker network (see `docker-compose.yml` for service names).

If you prefer a local, self-contained run for development, see `docs/OBSERVABILITY.md` for quick instructions.

## 🛠️ Development

- Windows: PowerShell scripts in `scripts/` (see `dev.ps1`, `quickstart.ps1`, `status.ps1`).
- Linux/Mac: Bash scripts in `scripts/` (see `dev.sh`, `quickstart.sh`, `status.sh`).
- Typical flow: create `.env`, install dependencies, run locally or via Docker. Use `check-all` for CI‑like checks.

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
- `METRICS_MODE` - scrape (default), push, both

See `.env.example` for full list.

### Advanced (events, progress, versions)
- `ENABLE_EVENTS` — enable Redis Pub/Sub events (default: true)
- `ENABLE_PROGRESS_EVENTS` — emit periodic progress updates (default: true)
- `PROGRESS_INTERVAL` — messages per progress update (default: 100)
- `FETCH_CONCURRENCY_PER_CHAT` — parallelism per chat (default: 3)
- `COMMENTS_LIMIT_PER_MESSAGE` — max comments to fetch per post (default: 50)
- `RATE_LIMIT_CALLS_PER_SEC` — API calls per second limit (default: 10.0)
- `MAX_PARALLEL_CHANNELS` — max channels processed in parallel (default: 3)
- `DEDUP_IN_RUN_ENABLED` — enable deduplication within a single run (default: false)

### Events bus (Redis)
- `REDIS_URL` — connection string (e.g., redis://localhost:6379)
- `REDIS_PASSWORD` — optional password
- `EVENTS_CHANNEL` — Pub/Sub channel name (default: tg_events)
- `SERVICE_NAME` — service identifier in events (default: tg_fetcher)
- `COMMANDS_QUEUE` — Redis list for command subscriber (default: tg_commands)
- `COMMANDS_BLPOP_TIMEOUT` — BLPOP timeout seconds (default: 5)

### Schema/processing versions
- `DATA_SCHEMA_VERSION` — version recorded in saved collections (default: 1)
- `PROGRESS_SCHEMA_VERSION` — version recorded in progress file (default: 1)
- `PREPROCESSING_VERSION` — version of preprocessing pipeline (default: 1)

### Storage backend
- `STORAGE_BACKEND` — `fs` (default) or `mongo`
  - For `mongo`, set:
    - `MONGO_URL` — connection string (e.g., mongodb://localhost:27017)
    - `MONGO_DB` — database name
    - `MONGO_COLLECTION` — collection name
  - Note: Mongo adapter is provided as a minimal scaffold. Use `fs` for the first production rollout unless Mongo is required.

## 🧭 CLI usage

Run for all configured chats (default):

```bash
tg-fetch run
```

Run a single chat for a specific date:

```bash
tg-fetch single @ru_python --date 2025-11-12
```

Start a long-running worker that listens to Redis commands queue:

```bash
tg-fetch listen --worker-id worker-1
```

Notes:
- Queue name and timeout come from `COMMANDS_QUEUE` and `COMMANDS_BLPOP_TIMEOUT`. You can override with `--queue` and `--timeout`.
- Command payload (JSON pushed to Redis list): `{ "command": "fetch", "chat": "ru_python", "date": "2025-11-12" }`.
- See `docs/CONFIGURATION.md` for details and examples.

### Enqueue a command manually

For local testing, you can push a command into the Redis queue using the helper script:

```powershell
# Windows PowerShell
.venv/Scripts/python.exe scripts/push_command.py --chat @ru_python --date 2025-11-12
```

This will enqueue a JSON payload into `COMMANDS_QUEUE` (default: `tg_commands`).

## 📦 Data Format

Messages are stored as JSON with versioned schema:

```json
{
  "version": "1.0",
  "timezone": "UTC",
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

- Observability & monitoring: `docs/OBSERVABILITY.md`
- Technical specification: `docs/tech_task/TZ-fetcher-improvements.md`
- Pre-implementation checklist: `docs/PRE_IMPLEMENTATION_CHECKLIST.md`
- Quick reference (fetcher): `docs/Fetcher_Quick_Reference.md`

## 🔍 Monitoring

See `docs/OBSERVABILITY.md` for Loki/Grafana/Prometheus quick instructions.

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
