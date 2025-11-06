#!/bin/bash
# Quick start script - full setup from scratch
# Run: ./scripts/quickstart.sh

set -e

echo "=========================================="
echo "Telegram Fetcher - Quick Start"
echo "=========================================="
echo ""

# Step 1: Check .env
echo "Step 1: Environment Setup"
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✓ .env created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your Telegram credentials:"
    echo "   - TELEGRAM_API_ID"
    echo "   - TELEGRAM_API_HASH"
    echo "   - TELEGRAM_PHONE"
    echo "   - TELEGRAM_CHATS"
    echo ""
    read -p "Press Enter after editing .env to continue..."
else
    echo "✓ .env exists"
fi
echo ""

# Step 2: Create Docker volumes
echo "Step 2: Creating Docker volumes for observability..."
docker volume create observability-stack_prometheus-data 2>/dev/null || true
docker volume create observability-stack_loki-data 2>/dev/null || true
docker volume create observability-stack_grafana-data 2>/dev/null || true
docker volume create observability-stack_pushgateway-data 2>/dev/null || true
echo "✓ Volumes created"
echo ""

# Step 3: Build and start services
echo "Step 3: Building and starting services..."
docker-compose up -d --build
echo "✓ Services started"
echo ""

# Step 4: Wait for services to be healthy
echo "Step 4: Waiting for services to be ready..."
sleep 10
echo "✓ Services should be ready"
echo ""

# Step 5: Show access info
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services are running:"
echo "  • Grafana:     http://localhost:3000 (admin/admin)"
echo "  • Prometheus:  http://localhost:9090"
echo "  • Loki:        http://localhost:3100"
echo "  • Pushgateway: http://localhost:9091"
echo ""
echo "View logs:"
echo "  docker-compose logs -f telegram-fetcher"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
