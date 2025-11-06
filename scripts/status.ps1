# Status check script for Windows - shows health of all services
# Run: .\scripts\status.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Telegram Fetcher - System Status" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if docker-compose is running
Write-Host "Docker Services:" -ForegroundColor Yellow
docker-compose ps
Write-Host ""

# Check volumes
Write-Host "Data Volumes:" -ForegroundColor Yellow
$dataSize = if (Test-Path data) { (Get-ChildItem data -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB } else { 0 }
$sessionsSize = if (Test-Path sessions) { (Get-ChildItem sessions -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB } else { 0 }
Write-Host "  • data/:     $([math]::Round($dataSize, 2)) MB"
Write-Host "  • sessions/: $([math]::Round($sessionsSize, 2)) MB"
Write-Host ""

# Check if services are accessible
Write-Host "Service Health:" -ForegroundColor Yellow

# Grafana
try {
    $response = Invoke-WebRequest -Uri http://localhost:3000 -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✓ Grafana:     http://localhost:3000" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Grafana:     Not accessible" -ForegroundColor Red
}

# Prometheus
try {
    $response = Invoke-WebRequest -Uri http://localhost:9090/-/healthy -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✓ Prometheus:  http://localhost:9090" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Prometheus:  Not accessible" -ForegroundColor Red
}

# Loki
try {
    $response = Invoke-WebRequest -Uri http://localhost:3100/ready -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✓ Loki:        http://localhost:3100" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Loki:        Not accessible" -ForegroundColor Red
}

# Pushgateway
try {
    $response = Invoke-WebRequest -Uri http://localhost:9091/-/healthy -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✓ Pushgateway: http://localhost:9091" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Pushgateway: Not accessible" -ForegroundColor Red
}

Write-Host ""

# Check recent logs for errors
Write-Host "Recent Errors (last 20 lines):" -ForegroundColor Yellow
$logs = docker-compose logs --tail=20 telegram-fetcher 2>$null | Select-String -Pattern "error" -CaseSensitive:$false
if ($logs) {
    $logs | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
} else {
    Write-Host "  No errors found" -ForegroundColor Green
}

Write-Host ""
Write-Host "For full logs: docker-compose logs -f telegram-fetcher" -ForegroundColor Gray
Write-Host ""
