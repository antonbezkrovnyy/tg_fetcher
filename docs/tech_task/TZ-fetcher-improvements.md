# ТЗ: Улучшения Telegram Fetcher (python-tg)

## 1. Бизнес-цель
Обеспечить более качественный, устойчивый и богато аннотированный сырый датасет для анализатора, снизить потери контекста и ускорить реакцию пайплайна. Повысить надёжность (ретраи, идемпотентность), добавить предобработку, метаданные и события прогресса.

## 2. Текущее состояние (аудит)
- Есть: fetcher_service (по дням / "yesterday"), daemon с Redis BLPOP командой, event_publisher (messages_fetched / fetch_failed), progress_tracker, стратегия по дате.
- Логика: скачивает все сообщения за день через iter_messages со срезом по UTC границам, сохраняет JSON коллекцию, публикует единичное событие по завершении.
- Нет: классификация сообщений, language/tag metadata, нормализация ссылок, объединение коротких последовательных сообщений одного автора, оценка токенов, промежуточные события прогресса, backoff для FloodWaitError, retry политики network, checksum файла в событии, метрики Prometheus, гибкая конфигурация ретраев, delta/incremental fetch, thread mapping, message type labeling, adaptive rate-limit handling.
- Неполно: отсутствует семантическая подготовка для будущего chunking (boundary hints, token budgeting).

## 3. Функциональные требования
1. Предобработка сообщений:
   - Нормализация ссылок (убрать UTM, сортировка параметров, стандарт http→https).
   - Объединение коротких подряд сообщений одного отправителя (≤120 символов, пауза ≤90 сек).
   - Классификация message_type: question | answer | code | log | spam | service | other (эвристики + опционально простая модель).
   - Language detection (ru/en/other) — добавляется поле lang.
   - Расчёт приблизительного token_count (эвристика по длине / simple tokenizer) для бюджетирования.

### 3.1 Реализация: текущий статус (на 2025‑11‑12)

- Выполнено:
   - Базовая нормализация ссылок и извлечение `normalized_links[]` (rule‑based, http→https, сортировка и очистка параметров UTM).
   - Оценка `token_count` для каждого сообщения (лёгкая эвристика) и агрегат `estimated_tokens_total` в summary.
   - Summary/threads/participants файлы генерируются per‑day; в summary присутствуют `schema_version`, `preprocessing_version`, `checksum`.
   - Промежуточные события прогресса и расширенное финальное событие с checksum и метаданными.
 - Частично (до обновления): retry/backoff, основные метрики.
 - Новые реализации (Фаза 2.1):
   - Merge коротких сообщений (порог длины и gap вынесены в конфиг: `MERGE_SHORT_MESSAGES_MAX_LENGTH`, `MERGE_SHORT_MESSAGES_MAX_GAP_SECONDS`).
   - Классификация `message_type` (эвристики: question/code/log/spam/service/answer/other).
   - Language detection (`lang`: ru/en/other) простая пропорция кириллица/латиница.
   - Нормализация ссылок + очистка UTM (уже была) — подтверждено.
   - Token estimate (эвристика *1.3) — подтверждено.
   - Idempotent checksum skip (если файл существует и checksum совпадает, публикуется событие `fetch_skipped`).
   - Prometheus progress gauge `fetch_progress_messages_current` (init=0, обновление на интервалах, сброс в 0 после завершения или skip).
   - Путь артефактов стандартизирован через публичные методы репозитория `get_output_file_path`, `get_summary_path`, `get_threads_path`, `get_participants_path`.
   - Событие `fetch_skipped` с reason + expected/actual checksum.
 - Не реализовано (отложено): Delta fetch режим, лимит сообщений per day.

### 3.2 Предлагаемый инкремент (Фаза 2.1 — предобработка) [Выполнено]

Включить следующие функции с конфиг‑флагами (по умолчанию включено, можно отключить в `.env`):

1) MERGE_SHORT_MESSAGES_ENABLED=true
    - Правила merge: один и тот же `sender_id`, расстояние между сообщениями ≤90 сек, длина каждого ≤120 символов; конкатенация с разделителем `\n\n` и комбинирование ссылок; обновить `token_count` и `normalized_links` после merge.
2) MESSAGE_CLASSIFIER_ENABLED=true
    - Правила (минимальный baseline):
       - `question`: содержит вопросительный знак, начинается с «как/почему/что/где/когда/можно ли», длина > 15.
       - `code`: присутствуют шаблоны кода (три бэктика, блоки с отступами, частые ключевые слова Python/JS), высокая доля небуквенных символов в строках.
       - `log`: содержит типичные метки времени/уровни (`ERROR`, `WARN`, stacktrace, traceback, Exception), длинные строки с `:` и путями.
       - `service`: присвоить системным сообщениям Telethon (joined/left/приглашения и т.п.).
       - `spam`: эвристики по ссылкам/ключевым словам, при низкой уверенности — `other`.
       - По умолчанию `other`.
3) LANGUAGE_DETECT_ENABLED=true
    - Простой детектор: доля кириллицы → `ru`, латиницы → `en`, иначе `other`; для коротких строк — `other`.

Дополнительно:
- Добавить `FETCH_PROGRESS_MESSAGES_CURRENT` (gauge) для текущего прогресса; лейблы: chat, date, worker.
- Idempotent checksum‑skip: если файл существует и checksum совпадает, при `FORCE_REFETCH=false` пропускать refetch с логом причины.

Acceptance для Фаза 2.1 (выполнено):
 - В дата‑файле поля: `message_type`, `lang`, `token_count`, `normalized_links[]`.
 - Merge работает по конфигурируемым порогам.
 - Gauge прогресса виден и сбрасывается.
 - Idempotent skip → событие `fetch_skipped` + лог `already_exists_same_checksum`.
2. Расширение сохранённого формата:
   - Добавить поля: token_count, message_type, normalized_links[], lang.
   - Создать summary файл per day: `<chat>/<date>_summary.json` (count, first_ts, last_ts, participants, link_domains, estimated_tokens_total, checksum).
3. Надёжность:
   - Retry policy для NetworkError (экспоненциальный backoff + jitter; макс попыток).
   - FloodWaitError → спать wait_seconds + jitter и повторить (не сразу publish fetch_failed).
   - Идемпотентность: если файл есть и checksum совпадает — не перефетчить (если force_refetch=false).
   - Частичное восстановление: если файл повреждён → rename + refetch.
4. События и прогресс:
   - Промежуточные events: `fetch_progress` каждые N (например, 500) сообщений с message_count_partial.
   - Окончательное событие `messages_fetched` расширить: добавить fields (checksum_sha256, token_estimate_total, first_message_ts, last_message_ts, schema_version, preprocessing_version).
   - Ввести поле schema_version=1.
5. Метрики / наблюдаемость (Prometheus):
   - fetch_duration_seconds (гистограмма).
   - fetch_messages_total (с label chat, date).
   - fetch_errors_total (error_type).
   - fetch_rate_limit_wait_seconds (summary).
   - fetch_retries_total.
   - fetch_progress_messages_current (gauge).
6. Конфигурация:
   - FETCH_RETRY_MAX (int)
   - FETCH_RETRY_BACKOFF_BASE (float, сек)
   - FETCH_RETRY_BACKOFF_JITTER (float 0..1)
   - FLOODWAIT_MAX_SLEEP (сек лимит)
   - PROGRESS_EVENT_INTERVAL (int сообщений)
   - LINK_NORMALIZE_ENABLED (bool)
   - MERGE_SHORT_MESSAGES_ENABLED (bool)
   - MESSAGE_CLASSIFIER_ENABLED (bool)
   - LANGUAGE_DETECT_ENABLED (bool)
   - TOKEN_ESTIMATE_ENABLED (bool)
   - DELTA_FETCH_ENABLED (bool)
7. Delta / Incremental fetch:
   - Поддержка команды `{"command":"fetch","chat":"...","date":"YYYY-MM-DD","mode":"delta"}` → загрузить только новые сообщения (msg.date > last_saved_date_max) и дописать/сливать в файл.
   - Публиковать событие `messages_delta_fetched`.
8. Thread mapping подготовка:
   - Формировать mapping: parent_id → [child_reply_ids], считать глубину.
   - Сохранить в отдельном файле `<chat>/<date>_threads.json`.
9. Checksum:
   - SHA256 сырого файла + отдельное поле в summary и в событии.
10. Token budget hint:
   - Подсчёт estimated_tokens_total → опубликование в событии для планирования chunking.
11. Безопасность:
   - Защита от избыточного объёма: лимит сообщений per day configurable (FETCH_DAY_MESSAGE_LIMIT) с логом truncation_warning.
12. Логирование:
   - Добавить correlation_id в промежуточные логи.
   - Лог причины пропуска (already_exists_same_checksum, partial_corrupt_refetch, delta_no_new_messages).
13. Стандартизация путей:
   - Перейти к формату `data/<chat>/<YYYY-MM-DD>.json` (без chat_id_ префикса внутри имени файла) для согласованности с анализатором.
   - Миграционный шаг: поддерживать чтение старого формата.
14. Ошибки:
   - Отдельное поле в fetch_failed событии: retryable=true/false.
   - Категоризация: auth_error, rate_limit, network_error, unknown_error, chat_not_found.

## 4. Ограничения и допущения
- Telethon не всегда даёт полный набор реакций/юзеров — не расширяем reactions до списка пользователей.
- Классификация сообщений на первом этапе rule-based (без нейросети).
- Incremental delta поддерживает только добавление новых сообщений (не удаление).

## 5. Архитектурные решения
- Расширить EventPublisher: новые методы publish_fetch_progress, publish_messages_delta.
- Внедрить Prometheus client (если глобально в observability пакете — переиспользовать).
- Thread mapping: простая in-memory сборка во время итерации (dict[parent]->list[child]); flush после полного прохода.
- Retry/backoff: обёртка вокруг `_process_date_range` или вокруг iter_messages цикла.
- Token estimate: лёгкий алгоритм (примерно: len(text.split())*1.3) или мини-токенизатор; хранить aggregated.

## 6. Конфигурационные ключи (префикс ENV)
```
FETCH_RETRY_MAX=3
FETCH_RETRY_BACKOFF_BASE=2.0
FETCH_RETRY_BACKOFF_JITTER=0.3
FLOODWAIT_MAX_SLEEP=600
PROGRESS_EVENT_INTERVAL=500
LINK_NORMALIZE_ENABLED=true
MERGE_SHORT_MESSAGES_ENABLED=true
MESSAGE_CLASSIFIER_ENABLED=true
LANGUAGE_DETECT_ENABLED=true
TOKEN_ESTIMATE_ENABLED=true
DELTA_FETCH_ENABLED=false
FETCH_DAY_MESSAGE_LIMIT=20000
SCHEMA_VERSION=1
PREPROCESSING_VERSION=1
```

## 7. План внедрения (фазы)
### Фаза 1 (Надёжность + базовая предобработка)
1. Retry/backoff (network + FloodWait).
2. Checksum + расширенный messages_fetched event.
3. Link normalization + token estimate + summary файл.
4. Thread mapping файл.
5. Prometheus метрики (duration, messages_total, errors_total).
6. Стандартизация пути файла (двойной режим чтения).

### Фаза 2 (Обогащение данных)
1. Классификация message_type + merge коротких сообщений.
2. Language detection.
3. Progress events (fetch_progress). 
4. Delta fetch режим.
5. Message limit + truncation логирование.

### Фаза 3 (Адаптивность + оптимизация)
1. Adaptive PROGRESS_EVENT_INTERVAL (на больших чатах увеличивать).
2. Token budget advisory events (fetch_budget_hint).
3. Active feedback для классификатора (если понадобится).
4. Optimization: batch write, async partial flush.
5. Additional metrics: progress gauge, rate_limit_wait_seconds.

## 8. Acceptance Criteria по фазам
- Фаза 1: успешные fetch события содержат checksum и token_estimate; ошибки классифицированы; retries выполняются согласно конфигу.
- Фаза 2: файл содержит новые поля (message_type, lang); дубликаты коротких сообщений снижены ≥15%; progress events публикуются; delta режим добавляет только новые записи.
- Фаза 3: уменьшение среднего времени до первого доступного частичного результата (progress event) ≤ 90 секунд; корректный бюджетный совет.

## 9. Метрики качества / наблюдаемости
- retry_count_avg
- rate_limit_events_total
- progress_events_total
- delta_fetch_invocations_total
- short_message_merges_total
- checksum_mismatch_incidents_total

## 10. Риски
| Риск | Смягчение |
|------|-----------|
| FloodWait долгий сон блокирует воркер | Параллелизм нескольких воркеров, лимит FLOODWAIT_MAX_SLEEP |
| Увеличение CPU от нормализации ссылок | Оптимизация: ранний skip при отсутствии 'http' |
| Ошибочная классификация message_type | Rule-based + лог для переобучения |
| Потенциальное расхождение формата файлов | Миграционный код чтения старого формата |
| Ошибки при delta merge | Валидация sorted по дате, проверка уникальности id |

## 11. Тестирование
- Юнит: link_normalize(), merge_short_messages(), classify_message_type().
- Интеграция: полный fetch дня → проверка наличия summary, thread mapping, event payload.
- Retry simulation: искусственно вызывать NetworkError → считать фактические попытки.
- Delta fetch: создать файл, добавить новые сообщения (mock), вызвать delta → проверить только прирост.

## 12. Логирование полей
Добавить в каждую ключевую запись: correlation_id, chat, date, phase (start_fetch, progress, save, publish_event), retry_attempt, wait_seconds.

## 13. Форматы файлов
- Raw: `data/<chat>/<YYYY-MM-DD>.json` (list сообщений + metadata header?).
- Summary: `data/<chat>/<YYYY-MM-DD>_summary.json`.
- Threads: `data/<chat>/<YYYY-MM-DD>_threads.json`.

## 14. Примечания
- Анализатор сможет использовать summary + threads для семантического chunking.
- Token estimate помогает заранее распределить chunk sizes.
- progress events открывают путь к раннему запуску анализатора (streaming mode — позже).

## 15. Статус
 - [x] ТЗ составлено
 - [x] Реализация Фаза 1 (основные метрики, checksum, summary, threads, retries baseline)
 - [x] Реализация Фаза 2.1 (предобработка: merge, classifier, lang, gauge, skip event)
- [ ] Реализация Фаза 2 (оставшиеся: delta fetch, лимит сообщений, расширенные retries конфиг)

## Deferred Items (Planned)
- Refactor to reduce cyclomatic complexity (flake8 C901) in `FetcherService` methods,
   primarily `_process_date_range` and related orchestration. Approach: extract
   helper functions (`_maybe_skip_existing`, `_publish_skip_and_reset`,
   `_update_progress_gauge`, `_preprocess_messages`, `_merge_short_messages`,
   `_classify_language`).
- Delta fetch design and implementation (semantics, idempotency rules, events).
- Test suite for preprocessing heuristics (merge thresholds boundaries, language
   detection edge cases, simple classifier) and idempotent skip scenarios.
- Metrics expansion (e.g., merged messages, language detection failures,
   classification unknowns, preprocess duration) — postponed.

Notes:
- Lint “0 violations” is not strictly required at this stage. A TODO marker has been
   added near the complex method to document the refactor plan.
- No additional Prometheus counters for skip events will be introduced in this phase.
 - [ ] Реализация Фаза 3
 - [ ] Тесты / Метрики / Документация (unit-tests для classifier/lang/merge/idempotent skip — запланированы)

### 15.1 Принятые решения (добавлено)
 - Skip event: формат `fetch_skipped` с полями reason, checksum_expected, checksum_actual.
 - Gauge стратегия: обновление только каждые `PROGRESS_INTERVAL` сообщений, reset → 0 после завершения/skip.
 - Merge пороги вынесены в конфиг (значения по умолчанию 120 символов / 90 секунд).
 - Idempotent критерий: только checksum совпадение (дополнительные проверки количества сообщений отложены).
 - Public path accessors в репозитории для унификации и тестируемости.

