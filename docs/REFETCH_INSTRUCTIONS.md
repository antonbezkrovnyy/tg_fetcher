# Инструкция: Перезапуск fetcher после исправлений

## Проблема
После исправления кода в `fetcher_service.py`:
1. ✅ Добавлена проверка `source_info.type != "channel"` в `_extract_comments()`
2. ✅ Добавлена проверка `entity.megagroup` в `_extract_source_info()`

Но данные в `data/*.json` **все еще содержат** старые значения:
- `"type": "channel"` вместо `"type": "supergroup"`
- Непустые `comments` в чатах

## Решение: Перезапустить fetcher

### Шаг 1: Убедиться что исправления применены

```powershell
cd c:\Users\Мой компьютер\Desktop\python-tg

# Проверить что код содержит исправления
Get-Content src\services\fetcher_service.py | Select-String "megagroup" -Context 2
# Должно быть:
#   if entity.megagroup:
#       source_type = "supergroup"
#   else:
#       source_type = "channel"

Get-Content src\services\fetcher_service.py | Select-String 'if source_info.type != "channel"' -Context 1
# Должно быть:
#   if source_info.type != "channel":
#       return comments_list
```

### Шаг 2: Проверить .env настройки

```powershell
# Открыть .env
code .env

# Убедиться что установлено:
FORCE_REFETCH=true

# Опционально: можно указать конкретные чаты
TELEGRAM_CHATS=@ru_python,@pythonstepikchat

# Режим: для пересбора конкретной даты
FETCH_MODE=date
FETCH_DATE=2025-11-06
```

### Шаг 3: Запустить fetcher

```powershell
cd c:\Users\Мой компьютер\Desktop\python-tg

# Активировать виртуальное окружение
.\.venv\Scripts\Activate.ps1

# Запустить fetcher
python -m src.main
```

**Ожидаемый вывод:**
```
INFO - Starting Telegram Fetcher Service
INFO - Fetching messages for @ru_python
INFO - Saved XXX messages
```

### Шаг 4: Проверить результат

```powershell
# Проверить тип источника (должно быть "supergroup")
Get-Content data\ru_python\2025-11-06.json | Select-String '"type":' | Select-Object -First 1
# Ожидаемый результат: "type": "supergroup"

# Проверить количество непустых comments (должно быть 0)
(Get-Content data\ru_python\2025-11-06.json | Select-String '"comments": \[\s*\{' | Measure-Object).Count
# Ожидаемый результат: 0

# Проверить pythonstepikchat тоже
Get-Content data\pythonstepikchat\2025-11-06.json | Select-String '"type":' | Select-Object -First 1
# Ожидаемый результат: "type": "supergroup"
```

### Шаг 5: Вернуть .env в нормальное состояние

```powershell
# После тестирования вернуть настройки:
code .env

# Изменить:
FORCE_REFETCH=false
FETCH_MODE=yesterday
# FETCH_DATE можно удалить или закомментировать
```

## Альтернатива: Пересобрать только нужные даты

Если нужно пересобрать только определенные даты:

```powershell
# В .env установить:
FETCH_MODE=range
FETCH_START=2025-11-05
FETCH_END=2025-11-06
FORCE_REFETCH=true
```

Или для одной даты:
```powershell
FETCH_MODE=date
FETCH_DATE=2025-11-06
FORCE_REFETCH=true
```

## Проверка что исправления работают

### 1. Тип источника
**До:**
```json
{
  "source_info": {
    "id": "@ru_python",
    "title": "ru_python",
    "type": "channel"  // ❌ НЕПРАВИЛЬНО
  }
}
```

**После:**
```json
{
  "source_info": {
    "id": "@ru_python",
    "title": "ru_python",
    "type": "supergroup"  // ✅ ПРАВИЛЬНО
  }
}
```

### 2. Комментарии
**До (для supergroup определенного как channel):**
```json
{
  "id": 2641183,
  "text": "Message",
  "comments": [  // ❌ Попытка извлечь комментарии
    {
      "id": 140432,
      "text": "Comment"
    }
  ]
}
```

**После (для supergroup):**
```json
{
  "id": 2641183,
  "text": "Message",
  "comments": []  // ✅ Пустой массив
}
```

## Время выполнения

- Для одной даты (~1000-5000 сообщений): **~5-15 минут**
- Зависит от rate limits Telegram API
- Прогресс отображается в логах

## Troubleshooting

### Проблема: "Skipping ... already completed"
**Решение:** Проверьте что `FORCE_REFETCH=true` в `.env`

### Проблема: Файлы не обновляются
**Решение:**
1. Проверьте время изменения файла: `(Get-Item data\ru_python\2025-11-06.json).LastWriteTime`
2. Убедитесь что fetcher запущен с исправленным кодом
3. Проверьте логи на ошибки

### Проблема: Все еще вижу `"type": "channel"`
**Решение:**
1. Проверьте что код содержит исправление: `Get-Content src\services\fetcher_service.py | Select-String "megagroup"`
2. Убедитесь что изменения сохранены
3. Перезапустите fetcher

## Логирование изменений

После успешного пересбора обновите console.log:

```
[2025-11-07 HH:MM:SS Testing] python -m src.main - Re-fetched data with megagroup fix
# Result: ru_python type changed from "channel" to "supergroup"
# Result: pythonstepikchat type changed from "channel" to "supergroup"
# Result: All comments arrays are now empty for supergroups
# Verification: checked data files, type is correct, comments=[]
```
