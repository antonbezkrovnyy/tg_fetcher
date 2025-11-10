# Исправление логики tg_fetcher для чатов

## Проблема
Fetcher извлекал `comments` для всех типов источников (каналов и чатов).
Но комментарии существуют только в каналах, в чатах используется `reply_to_msg_id`.

## Что исправили

### Файл: `src/services/fetcher_service.py`

**1. Добавили параметр `source_info` в `_extract_message_data()`:**
```python
async def _extract_message_data(
    self, client: TelegramClient, entity: Entity,
    message: TelethonMessage, source_info: SourceInfo  # NEW
) -> Message:
```

**2. Передаем `source_info` в `_extract_comments()`:**
```python
comments = await self._extract_comments(client, entity, message, source_info)
```

**3. Проверка типа источника в `_extract_comments()`:**
```python
async def _extract_comments(
    self, client: TelegramClient, entity: Entity,
    message: TelethonMessage, source_info: SourceInfo  # NEW
) -> list[Message]:
    """Extract comments from channel post discussion.

    Comments are only available for channels (type="channel"),
    not for chats/supergroups.
    In chats, replies are tracked via reply_to_msg_id field instead.
    """
    comments_list: list[Message] = []

    # Skip comments extraction for chats and supergroups
    # Comments are only for channels (type="channel")
    if source_info.type != "channel":  # NEW CHECK
        return comments_list

    # ... rest of logic for channels
```

## Результат

### До исправления:
```json
// Чат (type="chat")
{
  "id": 123,
  "text": "Message",
  "comments": [  // ❌ Попытка извлечь комментарии для чата
    {...}
  ]
}
```

### После исправления:
```json
// Чат (type="chat" или "supergroup")
{
  "id": 123,
  "text": "Message",
  "comments": []  // ✅ Пустой массив для чатов
}

// Канал (type="channel")
{
  "id": 456,
  "text": "Channel post",
  "comments": [  // ✅ Реальные комментарии для каналов
    {
      "id": 789,
      "text": "Comment",
      "sender_id": 111
    }
  ]
}
```

## Как протестировать

### Вариант 1: Перезапустить fetcher для одного дня
```powershell
cd c:\Users\Мой компьютер\Desktop\python-tg

# Активировать виртуальное окружение
.\.venv\Scripts\Activate.ps1

# Запустить с force-refetch для пересбора данных
python -m src.main --chat @ru_python --date 2025-11-05 --force-refetch
```

### Вариант 2: Проверить существующие данные
```powershell
# Посмотреть на существующий JSON файл
code data\ru_python\2025-11-05.json

# Найти любое сообщение с comments
# Для чата должно быть: "comments": []
```

### Вариант 3: Запустить тесты fetcher
```powershell
cd c:\Users\Мой компьютер\Desktop\python-tg

pytest tests/unit/test_fetcher_service.py -v
# Или
pytest tests/ -v -k "comments"
```

## Проверка в tg_analyzer

После исправления fetcher и пересбора данных:

```powershell
cd c:\Users\Мой компьютер\Desktop\tg_analyzer

# Запустить анализ с новыми данными
python scripts\test_real_analysis.py
```

Теперь validation не должен падать на пустых `comments` для чатов.

## Заметки

- ✅ Исправление не ломает обратную совместимость - старые данные все еще валидны
- ✅ Для каналов логика не меняется - комментарии извлекаются как раньше
- ✅ Для чатов производительность улучшится - не тратим время на попытку извлечь несуществующие комментарии
- ⚠️ Старые данные чатов могут содержать пустые `comments` или попытки извлечения - нужно пересобрать
- 📝 Обновленная документация: `docs/DATA_STRUCTURE.md` в tg_analyzer
