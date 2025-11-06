#!/bin/bash
set -e
set -x

MODE=${FETCH_MODE:-yesterday}

echo "Starting fetcher in mode: $MODE"

if [ "$MODE" = "full" ]; then
    echo "Running full historical fetch..."
    python -u -X faulthandler fetcher.py
elif [ "$MODE" = "yesterday" ]; then
    echo "Running yesterday-only fetch..."
    python -u -X faulthandler fetch_yesterday.py
else
    echo "Unknown mode: $MODE. Use 'full' or 'yesterday'"
    exit 1
fi

echo "Fetcher completed successfully"
