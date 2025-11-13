# Fetch Strategies

## Overview

Стратегии определяют, какие сообщения нужно скачать из чата/канала. Каждая стратегия отвечает на вопрос: "За какой период брать сообщения?"

## Available Strategies

### 1. YesterdayStrategy
- **Режим**: `yesterday`
- **Описание**: Сообщения только за вчерашний день
- **Использование**: Ежедневные обновления

```python
strategy = YesterdayStrategy()
# Вернет один диапазон: (вчера, вчера)
```

### 2. ByDateStrategy
- **Режим**: `date`
- **Описание**: Сообщения за конкретную дату
- **Параметры**: date_str в формате "YYYY-MM-DD"

```python
strategy = ByDateStrategy("2025-11-07")
# Вернет один диапазон: (2025-11-07, 2025-11-07)
```

### 3. FullHistoryStrategy
- **Режим**: `full`
- **Описание**: Все сообщения от начала до вчера
- **Особенности**:
  - Разбивает на недельные чанки
  - Идет от новых к старым
  - Поддерживает возобновление

```python
strategy = FullHistoryStrategy()
# Вернет диапазоны по 7 дней от вчера до первого сообщения
```

### 4. IncrementalStrategy
- **Режим**: `incremental`
- **Описание**: От последней обработанной даты до вчера
- **Особенности**:
  - Использует ProgressTracker
  - Пропускает уже обработанные даты
  - Поддерживает возобновление

```python
strategy = IncrementalStrategy(progress_tracker)
# Вернет диапазоны от last_processed до вчера
```

### 5. RangeStrategy
- **Режим**: `range`
- **Описание**: За указанный период
- **Параметры**: start_date, end_date ("YYYY-MM-DD")

```python
strategy = RangeStrategy("2025-10-01", "2025-10-31")
# Вернет диапазоны по дням в указанном периоде
```

## Implementation Details

### Base Strategy
```python
class BaseFetchStrategy(ABC):
    @abstractmethod
    async def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Get date ranges to fetch messages for."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass
```

### Key Principles
1. **Async Iterator**: Возвращает диапазоны по одному
2. **Date Based**: Работает с datetime.date
3. **Stateless**: Не хранит состояние (кроме IncrementalStrategy)
4. **Error Handling**: Валидирует входные данные

### Usage Example
```python
async def fetch_messages(strategy: BaseFetchStrategy):
    async for start_date, end_date in strategy.get_date_ranges():
        messages = await get_messages_for_range(start_date, end_date)
        await save_messages(messages)
```

## Testing Strategies

### Test Categories
1. **Дата возврата**: Правильные диапазоны
2. **Валидация**: Обработка неверных дат
3. **Пограничные случаи**: Пустые чаты, одно сообщение
4. **Прогресс**: Корректное отслеживание (для Incremental)

### Test Examples
```python
@pytest.mark.asyncio
async def test_yesterday_strategy():
    strategy = YesterdayStrategy()
    yesterday = date.today() - timedelta(days=1)

    ranges = [r async for r in strategy.get_date_ranges()]
    assert len(ranges) == 1
    assert ranges[0] == (yesterday, yesterday)

@pytest.mark.asyncio
async def test_full_history():
    strategy = FullHistoryStrategy()
    ranges = [r async for r in strategy.get_date_ranges()]

    # Проверяем:
    # - Каждый диапазон <= 7 дней
    # - От новых к старым
    # - Нет пропусков/пересечений
```
