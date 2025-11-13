param(
    [string]$SourcePath = "src",
    [string]$ReportDir = "typecov"
)

# Determine Python executable (prefer local venv)
$pythonExe = Join-Path ".venv" "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "py"
}

# Ensure report directory exists
if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir | Out-Null
}

# Run mypy with linecount report
& $pythonExe -m mypy --linecount-report "$ReportDir" $SourcePath
if ($LASTEXITCODE -eq 0) {
    Write-Host "Type coverage report generated at '$ReportDir'" -ForegroundColor Green
} else {
    Write-Host "mypy reported errors. See output above. Report may be partial at '$ReportDir'" -ForegroundColor Yellow
}
