# Sets environment for a one-off date fetch and runs the local test fetch script
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\fetch_ru_python_date.ps1

# Chat and date selection
$env:TELEGRAM_CHATS='["@ru_python"]'
$env:FETCH_MODE='date'
$env:FETCH_DATE='2025-11-03'

# Progress events: disable locally unless Redis is available
$env:ENABLE_PROGRESS_EVENTS='false'
$env:PROGRESS_INTERVAL='100'

# Redis: point to localhost for local runs (ignored when ENABLE_PROGRESS_EVENTS=false)
$env:REDIS_URL='redis://localhost:6379'

# Optional: force refetch if data already exists
$env:FORCE_REFETCH='true'

# Run the fetch test script (uses .env + these overrides)
py .\scripts\test_fetch_today.py
