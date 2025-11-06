# Multi-stage Dockerfile for Telegram Fetcher Service
# Stage 1: Builder - install dependencies
# Stage 2: Runtime - minimal production image

# === Stage 1: Builder ===
FROM python:3.11-slim AS builder

LABEL stage=builder
LABEL description="Build stage for installing Python dependencies"

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies to /app/.venv
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# === Stage 2: Runtime ===
FROM python:3.11-slim

LABEL maintainer="telegram-fetcher"
LABEL description="Production image for Telegram Fetcher Service"

# Create non-root user
RUN groupadd -r fetcher && useradd -r -g fetcher fetcher

# Set working directory
WORKDIR /app

# Install runtime dependencies only (if needed)
# Currently none required, but keep for future

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ /app/src/
COPY README.md /app/

# Create directories for data with proper permissions
RUN mkdir -p /app/data /app/sessions /app/logs && \
    chown -R fetcher:fetcher /app

# Switch to non-root user
USER fetcher

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check (optional - for continuous mode)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "-m", "src"]

# Volume mounts for data persistence
VOLUME ["/app/data", "/app/sessions"]

# Expose metrics port (if enabled)
EXPOSE 9090
