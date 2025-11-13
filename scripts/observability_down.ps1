param(
    [switch]$RemoveVolumes
)

$ErrorActionPreference = 'Stop'

Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
# go to repo root
Set-Location ..

$composeFile = 'docker-compose.observability.yml'
if ($RemoveVolumes) {
    docker compose -f $composeFile down -v
} else {
    docker compose -f $composeFile down
}

Write-Host "Observability stack is down." -ForegroundColor Yellow

Pop-Location
