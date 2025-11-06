# TZ: Telegram Messages Fetcher Service

## Business Goal

Создать сервис для периодического сбора (дампа) сообщений из Telegram каналов и чатов с сохранением в структурированном формате для последующего анализа.

## Functional Requirements

### Core Functionality
1. **Сбор сообщений из Telegram**
   - Поддержка публичных каналов (channels)
   - Поддержка чатов (chats)
   - Поддержка приватных каналов/чатов (при наличии доступа)
   - Сбор реакций к сообщениям (emoji reactions)
   - Сбор комментариев к постам в каналах (discussion threads)

2. **Режимы работы**
   - `yesterday` - сбор сообщений только за вчерашний день (по умолчанию)
   - `full` - полный сбор всей истории с начала до вчерашнего дня
   - `incremental` - сбор с последней обработанной даты до сегодня
   - `continuous` - непрерывный режим с отслеживанием прогресса
   - `date` - сбор за конкретную дату
   - `range` - сбор за диапазон дат

3. **Отслеживание прогресса**
   - Сохранение последней обработанной даты/позиции для каждого источника (канал/чат/пост)
   - Прогресс должен вестись во всех режимах (`yesterday`, `full`, `incremental`, `continuous`, `date`, `range`)
   - Возможность продолжить с места остановки
   - Защита от повторной обработки (idempotency)
   - Механизм полного сброса прогресса и точечного сброса (для конкретного источника/даты/поста)

4. **Управление данными**
   - Структурированное хранение по источникам и датам
   - JSON формат выходных файлов
   - Группировка `channels/` и `chats/` признана избыточной — использовать единую нейтральную структуру:
     `data/{source_name}/{YYYY-MM-DD}.json` (где `source_name` — уникальное имя/username/идентификатор канала или чата)
   - Формат файлов обязан содержать версию схемы (поле `version` в JSON)

### Data Structure

**Выходной формат JSON (версионируемая схема):**
```json
{
   "version": "1.0",
   "source_info": {
      "id": "@channel_username",
      "title": "Channel Title",
      "url": "https://t.me/channel_username"
   },
   "senders": {
      "123456": "Display Name"
   },
   "messages": [
      {
         "id": 12345,
         "date": "2025-11-06T10:30:00+00:00",
         "text": "Message text",
         "sender_id": 123456,
         "reply_to_msg_id": null,
         "forward_from": null,
         "reactions": {"👍": 12},
         "comments": []
      }
   ]
}
```

Примечания к модели:
- `version` — версия схемы файла.
- `reactions` — словарь emoji -> count (в дальнейшем можно расширить до списка пользователей).
- `comments` — массив сообщений той же схемы (используется для комментариев к постам каналов).
- `reply_to_msg_id` используется для связи ответов; это поле остаётся.
- `media_type` удаляется как избыточное поле — подробности о медиа хранятся в `message_utils`/attachments при необходимости.

### Progress Tracking Structure

**Формат файла `progress.json`:**
```json
{
  "version": "1.0",
  "sources": {
    "@ru_python": {
      "last_processed_date": "2025-11-05",
      "last_message_id": 12345,
      "last_updated": "2025-11-06T10:30:00+00:00",
      "status": "completed"
    },
    "@pythonstepikchat": {
      "last_processed_date": "2025-11-04",
      "last_message_id": 67890,
      "last_updated": "2025-11-05T15:20:00+00:00",
      "status": "in_progress"
    }
  }
}
```

**Операции сброса прогресса:**
- **Полный сброс**: удалить файл `progress.json` или установить `PROGRESS_RESET=true`
- **Точечный сброс**: удалить конкретный ключ из `sources` (по имени источника)
- **CLI команды** (будущее):
  ```bash
  # Полный сброс
  python -m src.main --reset-progress
  
  # Точечный сброс для конкретного источника
  python -m src.main --reset-progress-for @ru_python
  
  # Сброс за конкретную дату
  python -m src.main --reset-date 2025-11-05 --source @ru_python
  ```

### Non-Functional Requirements

1. **Надежность**
   - Обработка ошибок сети (retry mechanism)
   - Обработка Flood Wait от Telegram API
   - Graceful shutdown с сохранением прогресса
   - Healthcheck endpoint

2. **Производительность**
   - Rate limiting для соблюдения лимитов Telegram API
   - Поддержка ротации/множественности credentials (см. секцию конфигурации) для обхода/смягчения лимитов — возможность переключать credentials на лету
   - Async/await для параллельной обработки
   - Оптимизация запросов (не более 10 req/sec по умолчанию)

3. **Мониторинг и Observability**
   - Structured logging (JSON format)
   - Метрики Prometheus
   - Integration с observability-stack
   - Отслеживание: количество сообщений, время обработки, ошибки

4. **Безопасность**
   - Хранение API credentials в переменных окружения или в защищённом хранилище
   - Поддержка множества credentials и возможность их безопасной динамической подмены/ротации
   - Persistent session storage
   - Не коммитить session файлы

5. **Deployment**
   - Docker контейнеризация
   - docker-compose для оркестрации
   - Возможность запуска по расписанию (cron)

## Technical Decisions

### Database
- **Нет** - хранение в файловой системе (JSON files)
- Возможность миграции на БД в будущем (опционально)

### Framework & Libraries
- **Telegram Client**: Telethon 1.36+
- **Async Runtime**: asyncio (built-in)
- **Configuration**: python-dotenv для .env файлов
- **Logging**: python-json-logger для структурированных логов
- **Retry Logic**: tenacity для retry механизма
- **Metrics**: prometheus-client
- **Container**: Docker + docker-compose

### Architecture Patterns

1. **Strategy Pattern** - для разных режимов fetch
   - `ContinuousFetchStrategy`
   - `YesterdayOnlyFetchStrategy`
   - Легко добавлять новые стратегии

2. **Service Layer**
   - `FetcherService` - основной оркестратор
   - `SessionManager` - управление Telegram сессиями
   - `CredentialsManager` - управление пулом credentials и ротация
   - `RateLimiter` - контроль частоты запросов
   - `ProgressTracker` - отслеживание и сброс прогресса

3. **Repository Pattern** (опционально)
   - `MessageRepository` - сохранение/чтение сообщений
   - Абстракция над файловой системой

4. **Configuration Management**
   - Centralized config (`FetcherConfig`)
   - Validation на старте
   - Environment-based configuration

### Project Structure
```
src/
├── core/
│   └── config.py              # Configuration management
├── services/
│   ├── fetcher_service.py     # Main orchestrator
│   ├── session_manager.py     # Telegram session management
│   ├── credentials_manager.py # Credentials pool and rotation
│   ├── progress_tracker.py    # Progress tracking and reset
│   └── strategy/              # Fetch strategies
│       ├── base.py
│       ├── continuous.py
│       ├── yesterday.py
│       └── full.py
├── repositories/
│   └── message_repository.py  # Data persistence
├── utils/
│   ├── retry_utils.py         # Retry mechanisms
│   ├── rate_limiter.py        # Rate limiting
│   ├── message_utils.py       # Message processing (reactions, comments)
│   └── shutdown_utils.py      # Graceful shutdown
├── observability/
│   ├── logging_config.py      # Logging setup
│   ├── metrics.py             # Prometheus metrics
│   └── loki_handler.py        # Loki integration
└── main.py                    # Entry point
```

## API Design

### Configuration (Environment Variables)

**Required:**
```bash
# Telegram API credentials
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef1234567890
TELEGRAM_PHONE=+1234567890

# Channels/Chats to fetch (comma-separated)
TELEGRAM_CHATS=@ru_python,@pythonstepikchat
```

**Optional:**
```bash
# Fetch mode
FETCH_MODE=yesterday  # yesterday|full|incremental|continuous|date|range

# Paths
DATA_DIR=/data
SESSION_DIR=/sessions
PROGRESS_FILE=progress.json

# Support multiple credentials: either a directory with credential files or a JSON array of credentials
# Example: TELEGRAM_CREDENTIALS_DIR=/secrets/telegram_creds
# Or: TELEGRAM_CREDENTIALS_JSON='[{"api_id":111,"api_hash":"...","phone":"+..."}, {...}]'
TELEGRAM_CREDENTIALS_DIR=/secrets/telegram_creds

# Rate limiting
RATE_LIMIT_CALLS_PER_SEC=10.0
MAX_PARALLEL_CHANNELS=3

# Retry settings
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2.0

# Control for resetting progress (can also be exposed via CLI/API)
PROGRESS_RESET=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Observability
ENABLE_METRICS=true
METRICS_PORT=9090
LOKI_URL=http://loki:3100
```

### CLI Interface

```bash
# Запуск с режимом по умолчанию (yesterday)
python -m src.main

# Запуск с full режимом
FETCH_MODE=full python -m src.main

# Запуск за конкретную дату
FETCH_MODE=date FETCH_DATE=2025-11-01 python -m src.main

# Запуск за диапазон
FETCH_MODE=range FETCH_START=2025-11-01 FETCH_END=2025-11-05 python -m src.main

# Docker
docker-compose up fetcher

# Docker с переменными
FETCH_MODE=full docker-compose up fetcher
```

## Implementation Plan

### Phase 1: Core Infrastructure (MVP)
1. ✅ Изучить reference implementation (fetcher example)
2. Создать базовую структуру проекта
3. Настроить configuration management
4. Реализовать SessionManager для Telegram
5. Создать базовый FetcherService
6. Реализовать YesterdayOnlyStrategy
7. Добавить базовое логирование
8. Dockerfile и docker-compose

### Phase 2: Extended Functionality
1. Реализовать остальные стратегии (full, incremental, continuous)
2. Добавить retry механизм с tenacity
3. Реализовать RateLimiter
4. Добавить graceful shutdown
5. Healthcheck endpoint
6. Progress tracking и сохранение состояния
7. **Реализовать сбор реакций к сообщениям**
8. **Реализовать сбор комментариев к постам каналов**
9. **Реализовать механизм полного и точечного сброса прогресса**

### Phase 3: Observability
1. Интеграция с prometheus-client
2. Structured logging (JSON)
3. Loki handler для централизованных логов
4. Метрики: messages_fetched, fetch_duration, errors
5. Интеграция с observability-stack
6. **Реализовать ротацию credentials при достижении лимитов**

### Phase 4: Optimization & Production Ready
1. Тесты (unit + integration)
2. Error handling improvements
3. Performance optimization
4. Documentation (README, API docs)
5. CI/CD pipeline (.github/workflows)
6. Deployment guide

### Phase 5: Future Enhancements (Optional)
1. Web UI для мониторинга
2. REST API для управления
3. Database integration (PostgreSQL)
4. Message deduplication
5. Advanced filtering (по ключевым словам, пользователям)
6. Export в другие форматы (CSV, Parquet)

## Acceptance Criteria

### MVP (Phase 1)
- [ ] Сервис собирает сообщения за вчерашний день
- [ ] Данные сохраняются в JSON формате с версией схемы
- [ ] Работает авторизация через Telegram
- [ ] Session сохраняется между запусками
- [ ] Запускается через Docker
- [ ] Базовое логирование работает
- [ ] Единая структура хранения `data/{source_name}/{YYYY-MM-DD}.json`

### Full Product (Phases 2-3)
- [ ] Все режимы работы функционируют
- [ ] Retry механизм обрабатывает ошибки
- [ ] Rate limiting соблюдается
- [ ] Progress tracking работает корректно во всех режимах
- [ ] Механизм полного и точечного сброса прогресса реализован
- [ ] Реакции к сообщениям собираются и сохраняются
- [ ] Комментарии к постам каналов собираются и сохраняются
- [ ] Поддержка множественных credentials с ротацией при лимитах
- [ ] Метрики экспортируются в Prometheus
- [ ] Логи отправляются в Loki
- [ ] Healthcheck endpoint отвечает
- [ ] Graceful shutdown сохраняет состояние
- [ ] Покрытие тестами >80%
- [ ] Документация полная

## Dependencies

**Core:**
- telethon >= 1.36.0 (Telegram client)
- python-dotenv >= 1.0.0 (env variables)
- tenacity >= 8.2.3 (retry logic)

**Observability:**
- python-json-logger >= 2.0.7 (structured logging)
- prometheus-client >= 0.19.0 (metrics)
- requests >= 2.31.0 (Loki integration)

**Development:**
- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0
- pytest-cov >= 4.1.0
- black >= 24.0.0
- mypy >= 1.8.0

## Risks & Mitigations

### Risk 1: Telegram API Rate Limits
**Mitigation:** 
- Implement RateLimiter
- Configurable delays between requests
- Proper Flood Wait handling

### Risk 2: Large Channel History
**Mitigation:**
- Process day-by-day
- Save progress frequently
- Allow resumption from last checkpoint

### Risk 3: Session Invalidation
**Mitigation:**
- Persistent session storage
- Re-authentication flow
- Session backup mechanism

### Risk 4: Data Loss on Crash
**Mitigation:**
- Atomic file writes
- Save progress after each day
- Graceful shutdown handler

### Risk 5: Credential Rate Limits Exhaustion
**Mitigation:**
- Support multiple credentials pool
- Automatic rotation when hitting limits
- Flood Wait detection and credential switching
- Configurable cooldown periods per credential

### Risk 6: Comments/Reactions Data Completeness
**Mitigation:**
- Separate API calls for reactions and comments
- Proper error handling for missing/unavailable data
- Fallback to empty arrays/objects when data unavailable
- Log warnings for incomplete data collection

## Status
- [x] Requirements gathered
- [ ] Architecture designed
- [ ] Development started
- [ ] Testing completed
- [ ] Production deployed

## References
- Telethon Documentation: https://docs.telethon.dev/
- Telegram API Limits: https://core.telegram.org/api/obtaining_api_id
- Reference Implementation: `docs/examples/fetcher/`
- Observability Stack: https://github.com/antonbezkrovnyy/observability-stack
