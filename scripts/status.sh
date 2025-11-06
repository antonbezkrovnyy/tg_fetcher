#!/bin/bash
# Status check script - shows health of all services
# Run: ./scripts/status.sh

echo "=========================================="
echo "Telegram Fetcher - System Status"
echo "=========================================="
echo ""

# Check if docker-compose is running
echo "Docker Services:"
docker-compose ps
echo ""

# Check volumes
echo "Data Volumes:"
echo "  • data/:     $(du -sh data 2>/dev/null | cut -f1 || echo 'empty')"
echo "  • sessions/: $(du -sh sessions 2>/dev/null | cut -f1 || echo 'empty')"
echo ""

# Check if services are accessible
echo "Service Health:"

# Grafana
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✓ Grafana:     http://localhost:3000"
else
    echo "  ✗ Grafana:     Not accessible"
fi

# Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "  ✓ Prometheus:  http://localhost:9090"
else
    echo "  ✗ Prometheus:  Not accessible"
fi

# Loki
if curl -s http://localhost:3100/ready > /dev/null 2>&1; then
    echo "  ✓ Loki:        http://localhost:3100"
else
    echo "  ✗ Loki:        Not accessible"
fi

# Pushgateway
if curl -s http://localhost:9091/-/healthy > /dev/null 2>&1; then
    echo "  ✓ Pushgateway: http://localhost:9091"
else
    echo "  ✗ Pushgateway: Not accessible"
fi

echo ""

# Check recent logs for errors
echo "Recent Errors (last 20 lines):"
docker-compose logs --tail=20 telegram-fetcher 2>/dev/null | grep -i error || echo "  No errors found"

echo ""
echo "For full logs: docker-compose logs -f telegram-fetcher"
echo ""
