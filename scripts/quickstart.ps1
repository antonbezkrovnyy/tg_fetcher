# Quick start script for Windows - full setup from scratch
# Run: .\scripts\quickstart.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Telegram Fetcher - Quick Start" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check .env
Write-Host "Step 1: Environment Setup" -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Write-Host "Creating .env from template..." -ForegroundColor Gray
    Copy-Item .env.example .env
    Write-Host "✓ .env created" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit .env and add your Telegram credentials:" -ForegroundColor Red
    Write-Host "   - TELEGRAM_API_ID" -ForegroundColor White
    Write-Host "   - TELEGRAM_API_HASH" -ForegroundColor White
    Write-Host "   - TELEGRAM_PHONE" -ForegroundColor White
    Write-Host "   - TELEGRAM_CHATS" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter after editing .env to continue"
} else {
    Write-Host "✓ .env exists" -ForegroundColor Green
}
Write-Host ""

# Step 2: Create Docker volumes
Write-Host "Step 2: Creating Docker volumes for observability..." -ForegroundColor Yellow
docker volume create observability-stack_prometheus-data -ErrorAction SilentlyContinue | Out-Null
docker volume create observability-stack_loki-data -ErrorAction SilentlyContinue | Out-Null
docker volume create observability-stack_grafana-data -ErrorAction SilentlyContinue | Out-Null
docker volume create observability-stack_pushgateway-data -ErrorAction SilentlyContinue | Out-Null
Write-Host "✓ Volumes created" -ForegroundColor Green
Write-Host ""

# Step 3: Build and start services
Write-Host "Step 3: Building and starting services..." -ForegroundColor Yellow
docker-compose up -d --build
Write-Host "✓ Services started" -ForegroundColor Green
Write-Host ""

# Step 4: Wait for services to be healthy
Write-Host "Step 4: Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host "✓ Services should be ready" -ForegroundColor Green
Write-Host ""

# Step 5: Show access info
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are running:" -ForegroundColor White
Write-Host "  • Grafana:     http://localhost:3000 (admin/admin)" -ForegroundColor Gray
Write-Host "  • Prometheus:  http://localhost:9090" -ForegroundColor Gray
Write-Host "  • Loki:        http://localhost:3100" -ForegroundColor Gray
Write-Host "  • Pushgateway: http://localhost:9091" -ForegroundColor Gray
Write-Host ""
Write-Host "View logs:" -ForegroundColor White
Write-Host "  docker-compose logs -f telegram-fetcher" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop services:" -ForegroundColor White
Write-Host "  docker-compose down" -ForegroundColor Gray
Write-Host ""
