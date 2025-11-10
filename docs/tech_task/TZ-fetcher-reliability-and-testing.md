# TZ: Надёжность и качество фетчера (python-tg)

## Business Goal
Повысить надёжность, наблюдаемость и предсказуемость сервиса сбора сообщений из Telegram (python-tg), обеспечив стабильную обработку команд через Redis, корректную работу в режиме демона, метрики и алерты, а также покрытие тестами ключевых сценариев.

## Functional Requirements
1. Командная модель (Redis List `tg_commands`)
   - Поддерживаемые команды (JSON):
     - `{"command":"fetch","chat":"@ru_python","mode":"date","date":"YYYY-MM-DD","strategy":"batch"}`
     - `{"command":"fetch","chat":"@ru_python","mode":"days","days":N,"strategy":"batch"}`
     - `{"command":"fetch","chat":"@ru_python","mode":"range","from":"YYYY-MM-DD","to":"YYYY-MM-DD","strategy":"per_day"}`
   - Транспорт: BLPOP из списка `tg_commands` (таймаут настраиваемый)
   - Идемпотентность: Повторная постановка той же команды не должна дублировать данные
2. Событийная модель (Redis PubSub `tg_events`)
   - События: `started`, `progress`, `completed`, `failed`
   - Поля события (JSON): `command_id`, `chat`, `mode`, `date|from|to|days`, `processed`, `errors`, `duration_sec`, `status`
3. Режим демона
   - Непрерывная работа, корректное завершение по сигналу, безопасное восстановление после рестарта
   - Чтение команд, их исполнение, публикация событий, метрики
4. Хранилище данных
   - Формат: JSONL/JSON per-day (папки `data/<chat>/YYYY/`), пример: `data/ru_python/2025/discussions_2025-11-07.json`
   - Файл прогресса `data/progress.json` для идемпотентности/возобновления
5. Конфигурация через .env
   - TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
   - REDIS_URL (или REDIS_HOST/PORT/PASSWORD)
   - LOG_LEVEL, FETCH_CONCURRENCY, FETCH_STRATEGY
6. Ограничения Telegram (rate limiting)
   - Автоматическая обработка `FloodWait` с сном/бэкоффом
   - Конфигурируемый максимум ожидания и стратегия повторов

## Non-Functional Requirements
- Надёжность: безопасное восстановление, идемпотентность записи
- Производительность: обработка не менее X сообщений/мин (указать целевое значение на проде)
- Наблюдаемость: структурированные логи (метрики исключены из текущего этапа)
- Тестируемость: покрытие ключевой логики тестами (>80%)

## Data Contracts
1. Redis Command (JSON Schema, high-level)
```json
{
  "type": "object",
  "required": ["command", "chat", "mode"],
  "properties": {
    "command": {"enum": ["fetch"]},
    "chat": {"type": "string"},
    "mode": {"enum": ["date", "days", "range"]},
    "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "days": {"type": "integer", "minimum": 1},
    "from": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "to": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "strategy": {"enum": ["batch", "per_day"]},
    "options": {"type": "object"}
  }
}
```
2. Redis Event (PubSub)
```json
{
  "event": "started|progress|completed|failed",
  "command_id": "uuid",
  "chat": "@ru_python",
  "mode": "date|days|range",
  "params": {"date": "2025-11-07"},
  "processed": 271,
  "errors": 0,
  "duration_sec": 42.5,
  "ts": "2025-11-09T12:34:56Z"
}
```
3. Message JSON (выгрузка)
```json
{
  "id": 123,
  "date": "2025-11-07T10:23:45Z",
  "from_id": 4567890,
  "chat": "@ru_python",
  "text": "...",
  "reply_to": 122,
  "views": 1234,
  "forwards": 12,
  "replies_count": 5,
  "entities": [
    {"type": "url", "offset": 10, "length": 23}
  ]
}
```

## Logging & Diagnostics
1. Логирование (JSON)
   - Поля: `event`, `chat`, `command_id`, `mode`, `ts`, `level`, `duration_ms`, `error_type`
   - Фильтр против рекурсии (исключить `urllib3`, `requests`) для Loki handler
   - Корреляция операций по `command_id`
2. Диагностика
   - Подробные DEBUG-логи ключевых шагов (получение команды, разбор параметров, подключение к Telegram, чтение/запись файлов)
   - SAFE shutdown логи: начало/конец завершения, время ожидания, последняя обработанная команда

## Error Handling & Retry Policy
- Сетевые ошибки (timeout, connection): экспоненциальный бэкофф до N попыток
- `FloodWait`: спать `wait_sec + jitter`, ограничить максимум ожидания
- `RPCError`/`AuthKeyError`: логировать критическую ошибку, публиковать `failed`, остановить команду
- Ошибки Redis: повтор подключения с бэкоффом; при длительной недоступности — graceful shutdown
- Идемпотентность записи: проверка существования файла/записей, журнал прогресса

## Implementation Plan
A. Тестирование (P0)
1. Unit tests
   - Модели/валидаторы команд
   - Парсинг/нормализация дат
   - Экстрактор сообщений и маппинг полей
2. Integration tests
   - Обработка команд в Redis (BLPOP с тестовым Redis)
   - Публикация событий PubSub и их формат
   - Запись данных на диск и файл `progress.json`
3. E2E (локально/в CI с mock Telethon)
   - Полный цикл: команда → fetch → сохранение → событие (без метрик)

B. Логирование и диагностика (P1)
1. Внедрить `NoLoopFilter`, обеспечить структурированный формат логов
2. Добавить контекст `command_id` во все ключевые записи
3. Расширить DEBUG-логи по путям записи файлов и времени операций

C. Надёжность и восстановление (P1)
1. `progress.json` (пер-команда/пер-день) для safe resume
2. Проверки существования выходных файлов до записи
3. Точная семантика повторов (at-least-once, но без дублей в файлах)

D. CI (P1)
1. GitHub Actions: `black`, `isort`, `flake8`, `mypy`, `pytest --cov`
2. Публикация артефактов: отчёт покрытия, логи тестов
3. Опционально: smoke-test docker build

## Acceptance Criteria
- Команды из `tg_commands` обрабатываются для `date`, `days`, `range`
- Публикуются события в `tg_events` со схему-валидным JSON
- Unit+integration покрытие ≥ 80%; `pytest` зелёный
- Идемпотентность: повтор той же команды не создаёт дублей в файлах
- Логи структурированы, без рекурсивной петли в Loki handler
 - Корректная обработка `FloodWait` с уважением лимитов (тесты с имитацией)
 - SAFE shutdown корректно завершает выполнение без порчи данных
 - Валидация команд: некорректные команды отвергаются с событием `failed`

## Out of Scope
- Любые изменения в `tg_analyzer` и `tg_web`
- Миграции формата исторических файлов (только новый формат вперёд)
 - Метрики и алерты (перенесены на следующий этап)

## Risks & Mitigations
- FloodWait на большие интервалы → лимит ожидания и батчирование по дням
- Нестабильность сети → экспоненциальный бэкофф без алертов
- Рост очереди → масштабирование воркеров (алерты позже)

## Status
- [x] Draft
- [ ] In Progress
- [ ] Implemented
- [ ] Tested
