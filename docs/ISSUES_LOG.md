# Лог проблем и их решений

## 2025-11-06: Проблемы при запуске fetcher service

### Проблема 1: Infinite Recursion в Loki Handler при DEBUG уровне

**Симптомы:**
```
RecursionError: maximum recursion depth exceeded while calling a Python object
```

**Причина:**
При `LOG_LEVEL=DEBUG` логируются внутренние сообщения библиотек (urllib3, requests), которые используются для отправки логов в Loki. Это создаёт бесконечную рекурсию:

1. Loki handler пытается отправить лог → вызывает `requests.post()`
2. `urllib3` логирует DEBUG сообщение "Starting new HTTP connection..."
3. Это DEBUG сообщение попадает в Loki handler
4. Loki handler снова вызывает `requests.post()` для отправки этого лога
5. `urllib3` снова логирует → **рекурсия!**

**Решение:**
Настроить фильтр логов для Loki handler, чтобы исключить логи от urllib3/requests:

```python
# В src/observability/logging_config.py
class NoLoopFilter(logging.Filter):
    """Prevent logging loops by filtering out logs from HTTP libraries."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Exclude logs from urllib3 and requests to prevent recursion
        return not record.name.startswith(('urllib3', 'requests'))

# При добавлении Loki handler:
loki_handler.addFilter(NoLoopFilter())
```

**Временное решение (использовано):**
- Установить `LOG_LEVEL=INFO` (не DEBUG)
- Закомментировать `LOKI_URL` в `.env` при отладке


---

### Проблема 2: Сообщения не находятся - неправильная логика фильтрации по датам

**Симптомы:**
```
"No messages found for @ru_python on 2025-11-06"
```

Но при ручной проверке через `client.iter_messages(entity, limit=10)` сообщения **есть**!

**Причина:**
Первоначальная реализация использовала неправильную логику:

```python
# ❌ НЕПРАВИЛЬНО
offset_date = datetime.combine(end_date, datetime.max.time())  # 23:59:59
async for message in client.iter_messages(entity, offset_date=offset_date, reverse=True):
```

Проблемы:
1. `reverse=True` с `offset_date` начинает ОТ offset_date и идёт **вперёд** (к будущему)
2. Если `end_date` = сегодня, то `offset_date` = 23:59:59 сегодня
3. Но текущее время, например, 17:00
4. Условие `if msg_date > end_date: break` останавливает итерацию ДО того, как дойдём до сообщений
5. Или без `limit` итератор пытается получить **все** сообщения из истории канала → зависание

**Решение (из примера fetch_yesterday.py):**
```python
# ✅ ПРАВИЛЬНО
start = datetime(day_date.year, day_date.month, day_date.day, tzinfo=UTC)
end = start + timedelta(days=1)  # Начало следующего дня

async for msg in client.iter_messages(entity, offset_date=end, reverse=False):
    if msg_date >= end:
        continue
    if msg_date < start:
        break
```

Логика:
- `offset_date=end` - начинаем с **начала следующего дня**
- `reverse=False` (default) - идём **назад** (от новых к старым)
- `msg_date >= end: continue` - пропускаем сообщения из следующего дня
- `msg_date < start: break` - останавливаемся когда дошли до начала нашего дня


---

### Проблема 3: Зависание при iter_messages без limit

**Симптомы:**
Сервис начинает обработку, но никогда не завершается. CPU использование высокое.

**Причина:**
`client.iter_messages(entity)` без параметра `limit` пытается получить **все** сообщения из канала (могут быть десятки/сотни тысяч).

Даже с правильной логикой фильтрации, если условие `break` не срабатывает рано, итератор будет обрабатывать огромное количество сообщений.

**Решение:**
Добавить `limit` как safety механизм (например, `limit=10000` для одного дня).

**Примечание:**
В правильной реализации с `offset_date` и условием `if msg_date < start: break`, limit не обязателен, т.к. итерация останавливается естественным образом.


---

### Проблема 4: ❌ → ✅ РЕШЕНО: Зависание на iter_messages в _extract_comments()

**Симптомы:**
После исправления основной логики фетчинга, сервис всё ещё зависал при обработке комментариев.

**Причина:**
В методе `_extract_comments()` вызов `client.iter_messages()` **без limit**:

```python
# ❌ БЫЛО - зависание
async for comment in client.iter_messages(entity=entity, reply_to=message.id):
    comments.append({...})
```

Это пыталось получить **ВСЕ** комментарии из канала, а не только для конкретного сообщения.

**Решение:**
Добавлен `limit=50` для ограничения количества комментариев:

```python
# ✅ ИСПРАВЛЕНО
async for comment in client.iter_messages(
    entity=entity, 
    reply_to=message.id,
    limit=50  # Ограничение на комментарии к одному сообщению
):
    comments.append({...})
    comment_count += 1

logger.debug(f"Extracted {comment_count} comments for message {message.id}")
```

**Результаты тестирования (2025-11-06 21:42):**
- ✅ @ru_python: 543 сообщения сохранены в `data\ru_python\2025-11-06.json`
- ✅ @pythonstepikchat: 113 сообщений сохранены в `data\pythonstepikchat\2025-11-06.json`
- ✅ Логирование прогресса каждые 10 сообщений работает
- ✅ Нет зависаний, корректное завершение
- ✅ Telegram API flood wait обработан корректно (17 секунд)

**Commit:** Добавлен limit=50 для извлечения комментариев, добавлено логирование прогресса


---

### Проблема 5: Pydantic Settings v2 - JSON формат для list полей

**Симптомы:**
```
Failed to load configuration: error parsing value for field 'telegram_chats'
```

**Причина:**
Pydantic Settings v2 автоматически парсит JSON из environment variables для сложных типов.

**Решение:**
В `.env` использовать JSON формат:
```env
# ❌ НЕПРАВИЛЬНО
TELEGRAM_CHATS=@ru_python,@pythonstepikchat

# ✅ ПРАВИЛЬНО  
TELEGRAM_CHATS=["@ru_python","@pythonstepikchat"]
```

**Примечание:**
Не нужно создавать custom settings source - Pydantic делает это автоматически.


---

### Проблема 6: SessionManager initialization

**Симптомы:**
```
SessionManager.__init__() missing positional arguments (api_hash, phone, session_dir)
```

**Причина:**
Передавался весь `config` объект вместо отдельных параметров.

**Решение:**
```python
# ✅ ПРАВИЛЬНО
self.session_manager = SessionManager(
    api_id=config.telegram_api_id,
    api_hash=config.telegram_api_hash,
    phone=config.telegram_phone,
    session_dir=config.session_dir
)
```


---

### Проблема 7: Session filename с символом +

**Симптомы:**
Session file created but not found on next run.

**Причина:**
Phone number starts with `+`, which may cause issues in filenames.

**Решение:**
```python
safe_phone = phone.replace('+', '')
self._session_file = self.session_dir / f"session_{safe_phone}.session"
```


---

### Проблема 8: Async generator iteration

**Симптомы:**
```
TypeError: 'async_generator' object is not iterable
```

**Причина:**
Использовали `for` вместо `async for` для async generator.

**Решение:**
```python
# ❌ НЕПРАВИЛЬНО
for start_date, end_date in self.strategy.get_date_ranges(client, entity):

# ✅ ПРАВИЛЬНО
async for start_date, end_date in self.strategy.get_date_ranges(client, entity):
```


---

## TODO: Текущие задачи

- [ ] **КРИТИЧНО:** Исправить зависание при обработке сообщений
- [ ] Реализовать фильтр NoLoopFilter для Loki handler
- [ ] Добавить подробное логирование цикла обработки сообщений
- [ ] Проверить performance метода `_extract_message_data()`
- [ ] Добавить timeout для обработки одного канала
- [ ] Вернуть стратегию на `yesterday` (сейчас временно `today` для отладки)
- [ ] Написать unit тесты для date range logic
- [ ] Документировать все найденные проблемы в README

