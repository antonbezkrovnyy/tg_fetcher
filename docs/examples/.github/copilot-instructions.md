# Copilot Instructions for Telegram Fetcher Service

## Architecture Overview

This is a **Telegram message fetcher microservice** with a **Strategy Pattern** architecture. The codebase has undergone significant refactoring following **Test-Driven Development (TDD)** principles.

### Core Components

- **`FetcherService`** (`fetcher_service.py`) - Main orchestrator using Strategy pattern
- **`FetchStrategy`** - Abstract base for different fetching modes:
  - `ContinuousFetchStrategy` - Fetch from last checkpoint to today
  - `YesterdayFetchStrategy` - Fetch only yesterday's messages
- **`FetcherConfig`** (`config.py`) - Configuration with validation and multiple sources
- **`StandardMetrics`** (`common_observability.py`) - Unified observability with fallbacks
- **`SessionManager`** (`session_manager.py`) - Telegram session management

### Data Flow

```
config.py → FetcherService → FetchStrategy → fetch_day() → fetcher_utils.py → JSON files
     ↓            ↓              ↓             ↓               ↓
  validation   metrics    date ranges    Telegram API    message processing
```

## Development Patterns

### Configuration Management
```python
# ALWAYS use FetcherConfig, never hardcoded values
config = load_config()  # Loads from env vars or JSON file
# Supports: API credentials, paths, retry settings, rate limits
```

### Observability Pattern
```python
# Use common_observability.py for consistent metrics/logging
from common_observability import StandardMetrics, get_logger_safe
metrics = StandardMetrics()  # Auto-fallback if Prometheus unavailable
logger = get_logger_safe(__name__)  # Auto-fallback if observability unavailable
```

### Strategy Pattern Usage
```python
# FetcherService automatically selects strategy based on config.fetch_mode
service = FetcherService(config)
await service.run()  # Delegates to appropriate strategy
```

### Testing Infrastructure

**Critical**: Follow **TDD approach** - always write tests first, then implementation.

#### Test Structure
- `tests/conftest.py` - Shared fixtures (temp_data_dir, mock_telegram_client, etc.)
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Mock patterns**: Use `AsyncMock` for Telegram clients, `patch` for external dependencies

#### Key Test Patterns
```python
# For async generators (Telegram iter_messages)
async def mock_iter_messages(*args, **kwargs):
    yield mock_message
mock_client.iter_messages = mock_iter_messages  # NOT .return_value

# For configuration testing
with patch.dict('os.environ', {'API_ID': '12345'}):
    config = FetcherConfig.from_env()

# For observability fallbacks
with patch.dict('sys.modules', {'observability.metrics': None}):
    # Test graceful degradation
```

## Critical Development Commands

```bash
# Running tests (52 tests total as of current state)
pytest                                    # All tests
pytest tests/test_fetcher_service.py     # Specific module
pytest -m unit                           # Only unit tests
pytest --cov --cov-report=html          # With coverage

# Configuration testing
python -c "from config import load_config; print(load_config())"

# Entry points (NEW unified approach)
python unified_fetcher.py --mode yesterday
python unified_fetcher.py --mode continuous --channels channel1,channel2
```

## Key Conventions

### Error Handling
- Use `@retry_on_error_enhanced` decorator from `retry_utils.py`
- Handle `FloodWaitError` with exponential backoff
- Always record metrics for errors: `metrics.record_fetch_error(channel, error_type)`

### File Organization
- **Legacy files**: `fetcher.py`, `fetch_yesterday.py` (being replaced)
- **Current entry points**: `new_fetcher.py`, `new_fetch_yesterday.py`
- **Unified future**: `unified_fetcher.py` with CLI args

### Progress Tracking
```python
# Progress is stored as JSON: {"channel_name": "2024-01-15"}
progress_data = load_progress(config.progress_file)
progress_data[channel] = date.isoformat()
save_progress(config.progress_file, progress_data)
```

### Fallback Patterns
This codebase has **extensive fallbacks** for missing dependencies:
- `common_observability.py` provides Mock* classes when Prometheus/Loki unavailable
- All modules must handle missing observability gracefully
- Use `OBSERVABILITY_AVAILABLE` flag to check availability

## Integration Points

- **Telethon**: Telegram API client (sessions in `session_dir`)
- **Prometheus**: Metrics (optional, has fallbacks)
- **Loki**: Logging (optional, has fallbacks)
- **Docker**: Containerized deployment with volumes for `/data` and `/sessions`

## Common Gotchas

1. **Session paths**: Use `SessionManager`, never hardcode `/sessions/`
2. **Async mocking**: `iter_messages` needs function assignment, not `.return_value`
3. **Configuration**: Always validate via `FetcherConfig.__post_init__()`
4. **Date handling**: Use `UTC` timezone consistently, store as ISO strings
5. **Progress persistence**: Update after each successful day fetch, not batch