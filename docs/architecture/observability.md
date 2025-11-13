# Monitoring & Observability

## Components

### 1. Prometheus
- Сбор метрик
- Хранение временных рядов
- Запросы и алерты

### 2. Loki
- Сбор логов
- Индексация
- Поиск и агрегация

### 3. Grafana
- Визуализация метрик
- Дашборды
- Алерты

## Metrics

### Application Metrics

#### Message Stats
- `messages_fetched_total`: Счетчик сообщений
- `message_fetch_duration_seconds`: Время скачивания
- `message_size_bytes`: Размер сообщений

#### Operation Stats
- `operation_duration_seconds`: Время операций
- `operation_failures_total`: Счетчик ошибок
- `retry_attempts_total`: Счетчик ретраев

#### Resource Usage
- `memory_usage_bytes`: Использование памяти
- `cpu_usage_percent`: Использование CPU
- `goroutines_count`: Количество горутин

### Infrastructure Metrics

#### Redis Stats
- Queue size
- Operation latency
- Memory usage

#### Container Stats
- Container health
- Resource usage
- Network I/O

## Logging

### Log Format
```json
{
  "timestamp": "2025-11-09T12:34:56Z",
  "level": "INFO",
  "event": "message_fetched",
  "chat": "@channel",
  "message_id": 123,
  "duration_ms": 45
}
```

### Log Levels
- DEBUG: Детальная отладка
- INFO: Нормальные операции
- WARNING: Потенциальные проблемы
- ERROR: Ошибки операций
- CRITICAL: Критические сбои

### Context Fields
- operation_id: ID операции
- chat: Идентификатор чата
- strategy: Режим фетчинга
- duration: Время выполнения

## Dashboards

### Main Dashboard
- Message Stats
- Operation Stats
- Resource Usage
- Error Rates

### Chat Stats
- Messages per Chat
- Message Sizes
- Fetch Times
- Success Rates

### Error Analysis
- Error Types
- Error Rates
- Retry Stats
- Error Context

## Alerts

### Performance
- High Latency
- Low Throughput
- Resource Exhaustion

### Errors
- High Error Rate
- Failed Retries
- Critical Errors

### Infrastructure
- Service Down
- Queue Overflow
- Resource Limits

## Integration Guide

### Application Code
```python
import structlog
from prometheus_client import Counter, Histogram

# Metrics
messages_total = Counter(
    'messages_fetched_total',
    'Total messages fetched',
    ['chat', 'strategy']
)

fetch_duration = Histogram(
    'message_fetch_duration_seconds',
    'Time spent fetching messages',
    ['chat', 'strategy']
)

# Logging
logger = structlog.get_logger()

# Usage
def fetch_messages():
    with fetch_duration.time():
        messages = get_messages()
        messages_total.inc()
        logger.info('messages_fetched',
                   count=len(messages),
                   chat=chat_id)
```

### Docker Setup
```yaml
services:
  app:
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=8000"
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
```

## Best Practices

### Metrics
1. Используйте понятные имена
2. Добавляйте метки (labels)
3. Выбирайте правильный тип метрики
4. Документируйте метрики

### Logging
1. Структурированные логи
2. Правильные уровни
3. Контекст в логах
4. Не логируйте секреты

### Dashboards
1. Группируйте связанные метрики
2. Используйте тренды
3. Добавляйте описания
4. Настраивайте алерты

### General
1. Мониторьте все критичное
2. Настраивайте ретеншн
3. Регулярно проверяйте
4. Обновляйте алерты
