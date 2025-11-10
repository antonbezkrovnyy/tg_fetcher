# Quick Start Guide

## Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- Git (optional)

## One-Command Setup (Recommended)

### Windows
```powershell
.\scripts\quickstart.ps1
```

### Linux/Mac
```bash
chmod +x scripts/*.sh
./scripts/quickstart.sh
```

## Manual Setup

1. **Clone repository** (if not downloaded)
   ```bash
   git clone <repository-url>
   cd python-tg
   ```

2. **Setup environment**
   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env with your credentials:
   # - TELEGRAM_API_ID
   # - TELEGRAM_API_HASH
   # - TELEGRAM_PHONE
   # - TELEGRAM_CHATS
   ```

3. **Initialize observability volumes**
   ```bash
   docker volume create observability-stack_prometheus-data
   docker volume create observability-stack_loki-data
   docker volume create observability-stack_grafana-data
   docker volume create observability-stack_pushgateway-data
   ```

4. **Start services**
   ```bash
   docker-compose up -d --build
   ```

## Access Services

- **Grafana**: http://localhost:3000
  - Username: admin
  - Password: admin

## Basic Usage

1. **Check service health**
   ```bash
   docker-compose ps
   ```

2. **View logs**
   ```bash
   docker-compose logs -f telegram-fetcher
   ```

3. **Fetch messages**
   ```bash
   # Send fetch command
   python scripts/send_command.py --chat @channel_name --mode yesterday
   ```

## Next Steps

- [Detailed Installation Guide](./installation.md)
- [Development Guide](./development.md)
- [Deployment Guide](./deployment.md)