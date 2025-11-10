# Testing Guide

## Test Organization

```
tests/
├── unit/              # Unit tests
│   ├── test_strategy/
│   ├── test_models/
│   └── test_services/
│
├── integration/       # Integration tests
│   ├── test_fetch/
│   └── test_api/
│
└── conftest.py       # Shared fixtures
```

## Running Tests

### Basic Run
```bash
pytest
```

### With Coverage
```bash
pytest --cov=src tests/
```

### Only Unit Tests
```bash
pytest tests/unit/
```

### Single File
```bash
pytest tests/unit/test_strategy/test_yesterday.py
```

## Writing Tests

### Unit Test Example
```python
def test_yesterday_strategy():
    """Test YesterdayStrategy returns correct date range."""
    strategy = YesterdayStrategy()
    yesterday = date.today() - timedelta(days=1)
    
    ranges = [r async for r in strategy.get_date_ranges()]
    assert len(ranges) == 1
    assert ranges[0] == (yesterday, yesterday)
```

### Integration Test Example
```python
async def test_fetch_messages():
    """Test end-to-end message fetching."""
    client = await get_client()
    fetcher = MessageFetcher()
    
    result = await fetcher.fetch("@test_channel")
    assert result["success"]
    assert len(result["messages"]) > 0
```

### Mock Example
```python
def test_with_mock(mocker):
    """Test with mocked dependency."""
    mock_client = mocker.Mock()
    mock_client.get_messages.return_value = [
        Message(id=1, text="test")
    ]
    
    service = MessageService(mock_client)
    messages = service.get_messages()
    
    assert len(messages) == 1
    mock_client.get_messages.assert_called_once()
```

## Testing Best Practices

### 1. Test Organization
- Один тест - одна функциональность
- Группируйте похожие тесты в классы
- Используйте fixtures для повторного кода

### 2. Naming
- test_[что_тестируем]_[условия]_[ожидание]
- Понятные имена переменных
- Документация для сложных тестов

### 3. Assertions
- Конкретные проверки
- Понятные сообщения об ошибках
- Проверка исключений

### 4. Mocking
- Мокайте внешние зависимости
- Проверяйте вызовы моков
- Используйте spy где нужно

### 5. Fixtures
- Переиспользуемые объекты
- Разные уровни scope
- Параметризация где можно

## Coverage Goals

- Unit Tests: 90%+ coverage
- Integration Tests: Критические пути
- Edge Cases: Проверка граничных условий
- Error Paths: Проверка обработки ошибок