# Fetcher Service

Сервис для сбора сообщений из Telegram-каналов и чатов с использованием Telethon.

## Возможности

- **Два режима работы:**
  - `yesterday` — собирает только вчерашние сообщения (по умолчанию)
  - `full` — собирает всю историю с начала до вчерашнего дня
- **Отслеживание прогресса** — сохраняет последнюю обработанную дату для каждого канала
- **Persistent storage** — сессии Telegram сохраняются между запусками
- **Автоматическое определение** channels vs chats

## Структура

```
services/fetcher/
├── Dockerfile           # Образ контейнера
├── entrypoint.sh        # Точка входа (выбор режима)
├── fetcher.py           # Полный сбор истории
├── fetch_yesterday.py   # Сбор только за вчера
├── fetcher_utils.py     # Утилиты
└── requirements.txt     # Зависимости
```

## Использование

### 1. Подготовка

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Получите API credentials на https://my.telegram.org/auth

### 2. Первый запуск (авторизация)

При первом запуске нужно авторизоваться в Telegram:

```bash
# Создайте директорию для сессий
mkdir -p sessions

# Запустите интерактивно для авторизации
docker-compose -f docker-compose.fetcher.yml run --rm fetcher
```

Введите код из Telegram, после чего сессия сохранится в `sessions/`.

### 3. Обычный запуск

**Собрать вчерашние сообщения:**

```bash
docker-compose -f docker-compose.fetcher.yml up fetcher
```

**Собрать всю историю:**

```bash
FETCH_MODE=full docker-compose -f docker-compose.fetcher.yml up fetcher
```

### 4. Автоматизация

Добавьте в crontab для ежедневного запуска:

```cron
# Каждый день в 00:30 собирать вчерашние сообщения
30 0 * * * cd /path/to/project && docker-compose -f docker-compose.fetcher.yml up fetcher
```

## Выходные данные

Сообщения сохраняются в:

```
data/
├── channels/
│   └── ru_python/
│       ├── 2025-11-01.json
│       ├── 2025-11-02.json
│       └── ...
└── chats/
    ├── ru_python_beginners/
    │   └── 2025-11-01.json
    └── pythonstepikchat/
        └── 2025-11-01.json
```

Формат каждого файла:

```json
{
  "channel_info": {
    "id": "@ru_python",
    "title": "Python",
    "url": "https://t.me/ru_python"
  },
  "senders": {
    "123456": "Иван Иванов",
    "789012": "Мария Петрова"
  },
  "messages": [
    {
      "id": 12345,
      "ts": 1698883200,
      "text": "Текст сообщения",
      "reply_to": 12340,
      "reactions": 5,
      "sender_id": 123456
    }
  ]
}
```

## Прогресс

Прогресс сбора сохраняется в `data/progress.json`:

```json
{
  "@ru_python": "2025-11-01",
  "@ru_python_beginners": "2025-11-01"
}
```

## Troubleshooting

**Ошибка авторизации:**
- Удалите `sessions/session_digest.session` и пройдите авторизацию заново

**Контейнер не стартует:**
- Проверьте `.env` файл
- Убедитесь, что API_ID и API_HASH корректны

**Не находит канал:**
- Убедитесь, что вы подписаны на канал/чат
- Проверьте правильность username (с @ или без)
