# Fetcher Quick Reference (кратко)

Короткая шпаргалка по сервису `python-tg` для выгрузки сообщений Telegram.

## Что это

Сервис получает сообщения из заданных каналов/чатов, сохраняет структурированные JSON-данные и публикует события/метрики для наблюдаемости. Конфигурация задаётся через переменные окружения с валидацией (Pydantic v2).

## Как это работает (поток)

- Получение команды/запуска → выбор стратегии по `fetch_mode`
- Определение временных границ (дата/диапазон) и источников (чаты)
- Итерация сообщений Telethon с ограничением по датам и простым throttling
- Предобработка (нормализация ссылок, слияние коротких сообщений, классификация и т. п.)
- Сохранение в файловую систему или MongoDB, обновление прогресса/идемпотентность
- Публикация событий (Redis Pub/Sub) и метрик Prometheus; опционально — логи в Loki

## Ключевые возможности (коротко)

- Надёжность: единый retry/backoff с jitter + обработка FloodWait; circuit breaker для чувствительных операций
- Контроль нагрузки: `rate_limit_calls_per_sec`, параллельность по чатам и диапазонам
- Идемпотентность и дедупликация: прогресс по датам + `dedup_in_run_enabled`
- Богатая предобработка: нормализация ссылок, оценка токенов, слияние коротких сообщений, классификация, языковая метка
- События: старт/этап/прогресс/успех/ошибка/пропуск через Redis Pub/Sub
- Метрики: длительность, количество, ретраи, лаг свежести, прогресс; режимы scrape/push
- Хранилище: `fs` (по умолчанию) или `mongo` через DI-контейнер
- Наблюдаемость: структурированные логи (JSON/текст), опциональная отправка в Loki

## Режимы работы (`fetch_mode`)

- `yesterday` — выгрузка за вчера (по умолчанию)
- `full` — полная выгрузка исторических сообщений
- `incremental` — инкрементальная выгрузка от последнего прогресса
- `continuous` — длительный режим (демон) с обновлениями
- `date` — выгрузка за конкретную дату; требуется `fetch_date`
- `range` — выгрузка за диапазон дат; требуется `fetch_start` и `fetch_end`

## Минимальный запуск

Windows PowerShell (локально, без Docker):

```powershell
# 1) Подготовить .env c обязательными полями
Copy-Item .env.example .env
notepad .env   # TELEGRAM_API_ID/TELEGRAM_API_HASH/TELEGRAM_PHONE/TELEGRAM_CHATS

# 2) Запуск разовой выгрузки за вчера
$env:FETCH_MODE="yesterday"; tg-fetch run

# Альтернатива без консольного скрипта (если tg-fetch недоступен):
# .venv\Scripts\python.exe -m src run

# Пример выборочной даты по одному чату
tg-fetch single @ru_python --date 2025-11-12
```

Docker (если используете compose из монорепозитория):

```powershell
# Старт демона-воркера (слушает Redis-очередь команд)
docker compose up -d telegram-fetcher

# Пример постановки команды (см. scripts/push_command.py)
.venv\Scripts\python.exe scripts\push_command.py --chat @ru_python --date 2025-11-12
```

## Настройки (1 строка на поле)

Ниже — поля `FetcherConfig` (загружаются из `.env`/окружения), сгруппированные по смыслу.

### Telegram (обязательные)
- `telegram_api_id` — API ID из https://my.telegram.org/apps
- `telegram_api_hash` — 32-символьный API Hash
- `telegram_phone` — номер в формате `+1234567890`
- `telegram_chats` — список каналов/чатов (через запятую)

### Режим/даты
- `fetch_mode` — режим выгрузки: yesterday/full/incremental/continuous/date/range
- `fetch_date` — дата для режима `date` (YYYY-MM-DD)
- `fetch_start` — начало диапазона для `range` (YYYY-MM-DD)
- `fetch_end` — конец диапазона для `range` (YYYY-MM-DD)

### Пути
- `data_dir` — каталог для сохранения данных (JSON)
- `session_dir` — каталог для файлов сессий Telegram
- `progress_file` — файл прогресса выгрузки
- `telegram_credentials_dir` — каталог с несколькими кредами (опционально)

### Ограничения/параллелизм
- `rate_limit_calls_per_sec` — ограничение RPS Telethon
- `max_parallel_channels` — максимум каналов одновременно
- `fetch_concurrency_per_chat` — параллельных диапазонов на чат

### Повторы/устойчивость
- `max_retry_attempts` — число повторов при ошибках
- `retry_backoff_factor` — коэффициент экспоненциальной задержки

### Прогресс/события
- `progress_reset` — сбросить прогресс и начать сначала
- `force_refetch` — принудительно перекачать даже при наличии данных
- `enable_progress_events` — публиковать прогресс (Redis)
- `enable_events` — включить события старт/этап/успех/ошибка/пропуск
- `progress_interval` — шаг сообщений между событиями прогресса

### Предобработка
- `link_normalize_enabled` — извлечение и нормализация URL
- `token_estimate_enabled` — оценка количества токенов
- `merge_short_messages_enabled` — слияние коротких подряд сообщений
- `merge_short_messages_max_length` — макс. длина сообщения для слияния
- `merge_short_messages_max_gap_seconds` — макс. пауза между сообщениями
- `message_classifier_enabled` — правило‑бэйз классификация сообщений
- `language_detect_enabled` — простая метка языка (ru/en/other)

### Дедупликация
- `dedup_in_run_enabled` — дедупликат внутри одного запуска (сквозная идемпотентность по прогрессу действует всегда)

### Комментарии к постам
- `comments_limit_per_message` — лимит комментариев на пост (`0` отключает)

### Логи
- `log_level` — уровень логирования: DEBUG/INFO/WARNING/ERROR/CRITICAL
- `log_format` — формат логов: `json` или `text`
- `loki_url` — URL Loki для отправки логов (опционально)

### Метрики
- `enable_metrics` — включить экспорт метрик
- `metrics_port` — порт HTTP‑эндпойнта метрик
- `metrics_mode` — `scrape` (по умолчанию), `push` или `both`
- `pushgateway_url` — адрес Pushgateway (для `push`/`both`)

### Шина событий / Redis
- `events_channel` — имя канала Pub/Sub для событий
- `service_name` — имя сервиса в событиях/метриках
- `redis_url` — строка подключения Redis (redis://host:port)
- `redis_password` — пароль Redis (если требуется)

### Очередь команд (BLPOP)
- `commands_queue` — имя списка Redis для команд
- `commands_blpop_timeout` — таймаут BLPOP в секундах

### Версии схем/процесса
- `data_schema_version` — версия схемы сохранённых данных
- `progress_schema_version` — версия схемы прогресса
- `preprocessing_version` — версия пайплайна предобработки

### Хранилище
- `storage_backend` — `fs` или `mongo`
- `mongo_url` — URI MongoDB (при `storage_backend=mongo`)
- `mongo_db` — имя базы MongoDB
- `mongo_collection` — имя коллекции MongoDB

---

Для полного описания см. исходники `src/core/config.py`, а также разделы наблюдаемости в `docs/OBSERVABILITY.md`.
