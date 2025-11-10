# TZ: Tests Implementation and Service Completion

## Business Goal
Повысить надёжность и поддерживаемость кодовой базы путём добавления тестов и реализации недостающего функционала для сервисов telegram-fetcher, который уже частично реализован.

## Functional Requirements

### 1. Тестовое покрытие (Высокий приоритет)

#### 1.1 Unit Tests
```
tests/unit/
├── services/
│   ├── test_fetcher_service.py
│   │   └── Тестирование основного сервиса и метаданных
│   ├── test_progress_tracker.py
│   │   └── Тестирование механизмов прогресса
│   ├── test_session_manager.py
│   │   └── Тестирование управления сессиями
│   └── test_strategies/
│       ├── test_base.py
│       ├── test_yesterday.py
│       └── test_by_date.py
└── conftest.py
    └── Общие фикстуры
```

##### 1.1.1 Фикстуры (conftest.py)
- Mock для TelegramClient
- Mock для Message и MessageReactions
- Временные директории для данных/сессий
- Фейковые конфигурации

##### 1.1.2 Test Cases для FetcherService
- Инициализация с разными конфигурациями
- Обработка реакций (emoji reactions)
- Сохранение сообщений
- Rate limiting поведение
- Graceful shutdown

##### 1.1.3 Test Cases для ProgressTracker
- Сохранение/загрузка состояния
- Механизмы сброса (полный/частичный)
- Атомарность операций
- Формат JSON

##### 1.1.4 Test Cases для стратегий
- yesterday: корректность дат
- by_date: валидация формата
- Обработка ошибок

#### 1.2 Integration Tests
```
tests/integration/
├── test_fetcher_pipeline.py
├── test_progress_persistence.py
└── test_redis_integration.py
```

- End-to-end выборка за вчера
- Redis команды и их обработка
- Сохранение в файловую систему

### 2. Реализация стратегий (Средний приоритет)

#### 2.1 Новые стратегии
1. **FullHistoryStrategy**
   ```python
   class FullHistoryStrategy(BaseFetchStrategy):
       """Полная выборка с начала до вчера."""
       async def get_date_ranges(...):
           # Получить дату первого сообщения
           # Генерировать ranges до вчера
   ```

2. **IncrementalStrategy**
   ```python
   class IncrementalStrategy(BaseFetchStrategy):
       """С последней обработанной даты до сегодня."""
       async def get_date_ranges(...):
           # Взять last_processed_date из progress
           # Генерировать до today - 1
   ```

3. **RangeStrategy**
   ```python
   class RangeStrategy(BaseFetchStrategy):
       """Выборка за диапазон дат."""
       def __init__(self, start_date: str, end_date: str):
           # Валидация формата дат
   ```

### 3. Rate Limiting и Credentials (Низкий приоритет)

#### 3.1 RateLimiter Service
```python
class RateLimiter:
    """Rate limiting с поддержкой ротации credentials."""
    
    async def acquire(self) -> bool:
        """Проверка можно ли делать запрос."""
    
    async def rotate_credentials(self) -> None:
        """Переключение на другие credentials."""
```

#### 3.2 CredentialsManager
```python
class CredentialsManager:
    """Управление пулом credentials."""
    
    async def get_next(self) -> Credentials:
        """Получить следующие рабочие credentials."""
```

## Technical Decisions

### Testing Framework & Tools
- pytest
- pytest-asyncio для асинхронных тестов
- pytest-mock для моков
- pytest-cov для покрытия
- freezegun для тестов с датами

### Mocking Strategy
- Не мокать низкоуровневый Telethon API
- Мокать только внешние вызовы (сеть, файлы)
- Использовать реальные объекты где возможно

### Progress Format
```json
{
  "version": "1.0",
  "sources": {
    "@channel": {
      "last_processed_date": "2025-11-08",
      "last_message_id": 12345,
      "status": "completed"
    }
  }
}
```

## Implementation Plan

### Phase 1: Test Infrastructure (Дни 1-2)
1. Создать структуру папок
2. Настроить фикстуры
3. Базовые тесты для существующего

### Phase 2: Service Tests (Дни 3-4)
1. FetcherService тесты
2. ProgressTracker тесты
3. Дополнить по результатам

### Phase 3: Strategy Implementation (Дни 5-7)
1. Написать тесты для новых стратегий
2. Реализовать стратегии
3. Интеграционные тесты

### Phase 4: Rate Limiting (Дни 8-9)
1. Реализовать RateLimiter
2. Добавить CredentialsManager
3. Интеграционные тесты

## Acceptance Criteria

### Testing (Must Have)
- [ ] Структура тестов создана
- [ ] Фикстуры работают
- [ ] Покрытие >80%
- [ ] Тесты проходят быстро (<30s)

### Strategies (Should Have)
- [ ] Все стратегии реализованы
- [ ] Каждая стратегия имеет тесты
- [ ] Документация обновлена

### Rate Limiting (Could Have)
- [ ] Ротация credentials работает
- [ ] Graceful shutdown реализован
- [ ] Метрики добавлены

## Dependencies

**Testing:**
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
freezegun>=1.2.0
```

## Risks & Mitigations

### Risk 1: Медленные тесты
**Mitigation:**
- Мокать внешние вызовы
- Параллельный запуск
- Метки для медленных тестов

### Risk 2: Флакающие тесты
**Mitigation:**
- Фиксированные random seeds
- Временные фикстуры
- Retries для интеграционных

### Risk 3: Сложность с Telethon API
**Mitigation:**
- Абстракция для тестов
- Отдельные e2e тесты
- Документированные моки

## Status
- [ ] In Progress
- [ ] Implemented
- [ ] Tested