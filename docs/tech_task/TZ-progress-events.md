# TZ: Прогресс-ивенты в фетчере Telegram

## Business Goal
Давать внешним сервисам (tg_analyzer, tg_web) онлайн‑видимость процесса выгрузки: что именно сейчас обрабатывается, сколько сообщений уже пройдено, оценку прогресса/ETA и стадии пайплайна. Это поможет показывать прогресс в UI и триггерить последующие шаги по мере готовности.

## Functional Requirements
  - `fetch_started` — начало обработки даты/диапазона для источника.
  - `fetch_progress` — периодические обновления (каждые N сообщений или по таймеру).
  - `fetch_stage` — смена стадии пайплайна ("fetching", "saving", "postprocess").
  - (опционально) `fetch_completed` — явное завершение этапа (закрывает цикл; дублируется `messages_fetched`).

## Event Schema (предлагаемые поля)
- `source`: string (идентификатор чата, например "@ru_python" или numeric id)
- `date`: string YYYY-MM-DD (целевая дата выгрузки)
Дополнительно:
- `fetch_started`:
  - `strategy`: string (например, "ByDateStrategy"/"YesterdayOnlyStrategy")
- `fetch_progress`:
  - `messages_processed`: int (сколько сообщений просмотрено итератором)
  - `progress_pct`: float (0..100, при наличии total_estimate)
- `fetch_stage`:
  - `stage`: "fetching" | "saving" | "postprocess"
- `fetch_completed`:
  - `message_count`: int
  - `duration_seconds`: float
Примечания:
- Если невозможно оценить `total_estimate`, `progress_pct` и `eta_seconds` могут отсутствовать или быть `null`.

## Transport

## Hook Points
- `FetcherService._process_date_range`:
  - Перед началом цикла — `fetch_started` + `fetch_stage(stage="fetching")`.
  - Внутри цикла по сообщениям — `fetch_progress` каждые N сообщений (N=100 по умолчанию).
  - Перед сохранением — `fetch_stage(stage="saving")`.
## Конфигурация
- Добавить параметр (например, `progress_interval`) в конфиг фетчера (по умолчанию 100).
## Backward Compatibility
- Не меняем существующие методы публикации в `EventPublisher`.
- Добавляем новые методы:
  - `publish_fetch_started(source, date, strategy)`
  - `publish_fetch_stage(source, date, stage)`
  - (опц.) `publish_fetch_completed(...)` при необходимости явного семантического закрытия.
## Metrics
- Инкрементировать счетчики для отправленных прогресс-сообщений (например, `fetch_progress_events_total`).
- Гистограмму времени между публикациями можно добавить позже (необязательно на первом шаге).

## Implementation Plan
1. Расширить `EventPublisher` новыми методами публикации прогресса/стадий.
2. Добавить настройки `progress_interval` и `enable_progress_events` в `FetcherConfig`.
3. Внедрить вызовы публикации в `FetcherService._process_date_range` (точки: старт, каждые N сообщений, смена стадий, завершение).
4. Минимальные unit-тесты на сериализацию событий и частоту (моки Redis).
- [ ] Approved
- [ ] Implemented
- [ ] Tested
