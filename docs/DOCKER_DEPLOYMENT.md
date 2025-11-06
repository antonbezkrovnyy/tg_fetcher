# Docker Deployment Guide

## Quick Start

### 1. Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- Git

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Telegram credentials
# REQUIRED:
#   TELEGRAM_API_ID
#   TELEGRAM_API_HASH
#   TELEGRAM_PHONE
#   TELEGRAM_CHATS
```

### 3. Initialize Observability Stack

First time setup - create volumes for observability-stack:

```bash
# Create external volumes
docker volume create observability-stack_prometheus-data
docker volume create observability-stack_loki-data
docker volume create observability-stack_grafana-data
docker volume create observability-stack_pushgateway-data
```

### 4. Run Services

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

## Service URLs

Once running, access:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100
- **Pushgateway**: http://localhost:9091

## Viewing Logs

```bash
# View fetcher logs
docker-compose logs -f telegram-fetcher

# View all logs
docker-compose logs -f

# In Grafana:
# 1. Go to Explore
# 2. Select Loki data source
# 3. Query: {service="telegram-fetcher"}
```

## Viewing Metrics

In Grafana:
1. Go to Explore
2. Select Prometheus data source
3. Query metrics (e.g., `telegram_messages_fetched_total`)

## Data Persistence

Data is stored in:
- `./data/` - Fetched messages (JSON files)
- `./sessions/` - Telegram session files
- `./progress.json` - Fetch progress tracking

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Troubleshooting

### Volume Errors

If you see "volume not found" errors:

```bash
# Re-create volumes
docker volume create observability-stack_prometheus-data
docker volume create observability-stack_loki-data
docker volume create observability-stack_grafana-data
docker volume create observability-stack_pushgateway-data
```

### Permission Issues

```bash
# Fix permissions on Linux
sudo chown -R $USER:$USER data sessions
```

### Rebuild After Code Changes

```bash
# Rebuild fetcher service
docker-compose build telegram-fetcher

# Restart with new build
docker-compose up -d telegram-fetcher
```

## Production Deployment

For production, consider:

1. **Use secrets management** (Docker Secrets, Vault)
2. **Set resource limits** in docker-compose.yml
3. **Enable log rotation**
4. **Backup data directories regularly**
5. **Monitor resource usage**

### Resource Limits Example

Add to telegram-fetcher service:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## Monitoring Health

```bash
# Check service health
docker-compose ps

# Check logs for errors
docker-compose logs telegram-fetcher | grep ERROR

# View resource usage
docker stats
```
