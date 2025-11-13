param(
    [switch]$Recreate
)

$ErrorActionPreference = 'Stop'

Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
# go to repo root
Set-Location ..

# Ensure docker network exists
$netName = 'tg-infrastructure'
$netExists = docker network ls --format '{{.Name}}' | Select-String -SimpleMatch $netName
if (-not $netExists) {
    Write-Host "Creating docker network '$netName'" -ForegroundColor Cyan
    docker network create $netName | Out-Null
}

$composeFile = 'docker-compose.observability.yml'
if ($Recreate) {
    docker compose -f $composeFile down
}

docker compose -f $composeFile up -d

Write-Host "Observability stack is up: Grafana: http://localhost:3000, Prometheus: http://localhost:9090, Loki: http://localhost:3100, Pushgateway: http://localhost:9091" -ForegroundColor Green

Pop-Location
