# Contributing Guide

## Development Setup

### 1. Environment Setup
```bash
# Create venv
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Pre-commit Setup
```bash
# Install pre-commit
pre-commit install
```

### 3. Docker Setup
```bash
# Create volumes
docker volume create observability-stack_prometheus-data
docker volume create observability-stack_loki-data
docker volume create observability-stack_grafana-data
docker volume create observability-stack_pushgateway-data

# Start services
docker-compose up -d
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature
```

### 2. Code Quality
```bash
# Format code
black .
isort .

# Check
flake8
mypy src/

# Run tests
pytest
```

### 3. Commit Changes
```bash
# Use conventional commits
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git commit -m "docs: update readme"
```

### 4. Create PR
1. Push branch
2. Create Pull Request
3. Wait for review
4. Address feedback
5. Merge when approved

## Code Style

### Python Style
- Black formatting
- Type hints everywhere
- Google style docstrings
- Max line length: 88

### Import Style
```python
# Standard library
import os
from datetime import datetime

# Third party
import redis
from telethon import TelegramClient

# Local
from src.services import MessageService
```

### Function Style
```python
def process_message(
    message_id: int,
    content: str,
    *,
    save: bool = False
) -> dict[str, Any]:
    """Process a message.

    Args:
        message_id: Message identifier
        content: Message content
        save: Whether to save result

    Returns:
        Processed message data

    Raises:
        ValueError: If content is empty
    """
    if not content:
        raise ValueError("Content required")
    # Implementation
```

### Class Style
```python
class MessageProcessor:
    """Processes messages with retry logic."""

    def __init__(self, retries: int = 3):
        """Initialize processor.

        Args:
            retries: Max retry attempts
        """
        self.retries = retries

    async def process(self, message_id: int) -> None:
        """Process single message."""
```

## Testing

### Unit Tests
```python
def test_message_processing():
    """Test message processing logic."""
    processor = MessageProcessor()
    result = processor.process("test")
    assert result.status == "success"
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_fetch_messages():
    """Test end-to-end fetch."""
    client = await get_client()
    messages = await fetch_messages(client)
    assert len(messages) > 0
```

### Fixtures
```python
@pytest.fixture
def processor():
    """Create test processor."""
    return MessageProcessor(retries=1)
```

## Documentation

### Code Comments
- Сложная логика
- Неочевидные решения
- TODO с номером issue

### Docstrings
- Все публичные функции/классы
- Параметры и возвращаемые значения
- Примеры где нужно

### Project Docs
- README.md: Обзор проекта
- CONTRIBUTING.md: Гайд разработчика
- docs/: Детальная документация

## Release Process

### 1. Version Bump
- Обновить версию в `pyproject.toml`
- Обновить CHANGELOG.md

### 2. Testing
- Прогнать все тесты
- Проверить в dev окружении
- Проверить миграции

### 3. Documentation
- Обновить README если нужно
- Проверить API документацию
- Добавить release notes

### 4. Release
- Создать tag
- Push в master
- Проверить CI/CD
- Мониторить деплой