# Fetcher Service MVP+ 🚀

Production-ready сервис для сбора сообщений из Telegram с улучшениями:
- ✅ Structured JSON logging с VictoriaLogs
- ✅ Автоматический retry с exponential backoff
- ✅ FloodWait handling для Telegram rate limits
- ✅ Graceful shutdown
- ✅ Healthcheck для Docker

## 📋 Быстрый старт

### 1. Базовая настройка

```bash
# Копируйте .env.example в .env
cp .env.example .env

# Отредактируйте .env с вашими credentials
# API_ID и API_HASH получите на https://my.telegram.org/auth
```

### 2. Запуск без VictoriaLogs (простой режим)

```bash
# Сборка
docker-compose -f docker-compose.fetcher.yml build

# Первый запуск (нужна авторизация в Telegram)
docker-compose -f docker-compose.fetcher.yml run --rm fetcher

# Обычный запуск (собрать вчерашние сообщения)
docker-compose -f docker-compose.fetcher.yml up fetcher

# Проверка healthcheck
docker inspect telegram-fetcher --format='{{.State.Health.Status}}'
```

### 3. Запуск с VictoriaLogs (полный мониторинг)

```bash
# Запустите VictoriaLogs
docker-compose -f docker-compose.victoria.yml up -d

# Убедитесь, что в .env указан:
# VICTORIA_LOGS_URL=http://victoria-logs:9428/insert/jsonline

# Запустите fetcher
docker-compose -f docker-compose.fetcher.yml up fetcher

# Откройте Grafana для просмотра логов
# http://localhost:3000 (admin/admin)
```

## 🔍 Мониторинг и логи

### Просмотр логов в консоли

```bash
# Structured JSON логи
docker-compose -f docker-compose.fetcher.yml logs -f fetcher

# Только ошибки
docker-compose -f docker-compose.fetcher.yml logs fetcher | grep '"level":"ERROR"'
```

### Просмотр логов в VictoriaLogs

```bash
# Web UI
open http://localhost:9429

# Запрос через API
curl 'http://localhost:9428/select/logsql/query' -d 'query=_stream:{service="telegram-fetcher"} | limit 100'

# Поиск ошибок
curl 'http://localhost:9428/select/logsql/query' -d 'query=_stream:{service="telegram-fetcher"} level:ERROR'

# Статистика по каналам
curl 'http://localhost:9428/select/logsql/query' -d 'query=_stream:{service="telegram-fetcher"} | stats count() by channel'
```

### Healthcheck

```bash
# Статус контейнера
docker ps

# Детальная информация
docker inspect telegram-fetcher | jq '.[0].State.Health'

# Файловый healthcheck
docker exec telegram-fetcher cat /tmp/.fetcher_healthy | jq
```

## ⚙️ Конфигурация

### Переменные окружения

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
VICTORIA_LOGS_URL=http://...      # URL VictoriaLogs (пусто = отключено)
ENVIRONMENT=production            # production, development, staging

# Retry logic
MAX_RETRIES=3                     # Количество попыток при ошибке
MIN_RETRY_WAIT=1                  # Минимальное ожидание (секунды)
MAX_RETRY_WAIT=60                 # Максимальное ожидание (секунды)
REQUESTS_PER_SECOND=1.0           # Rate limiting

# Fetcher mode
FETCH_MODE=yesterday              # yesterday или full
```

### Режимы работы

**Yesterday mode (по умолчанию):**
```bash
docker-compose -f docker-compose.fetcher.yml up fetcher
```

**Full historical mode:**
```bash
FETCH_MODE=full docker-compose -f docker-compose.fetcher.yml up fetcher
```

## 🛡️ Обработка ошибок

### Автоматический retry

Сервис автоматически повторяет запросы при временных ошибках:
- Сетевые ошибки (ConnectionError, TimeoutError)
- Временные ошибки Telegram API (500, 503)
- Exponential backoff: 1s → 2s → 4s → ... → 60s

### FloodWait handling

При rate limiting от Telegram:
- Автоматически ждёт указанное время + 5 секунд
- Логирует время ожидания
- Продолжает работу после ожидания

### Graceful shutdown

При SIGTERM/SIGINT:
- Завершает текущую задачу
- Сохраняет прогресс
- Закрывает соединения
- Таймаут 30 секунд, затем force kill

## 📊 Примеры логов

### Успешный fetch

```json
{
  "timestamp": "2025-11-03T10:30:45.123456+00:00",
  "level": "INFO",
  "service": "telegram-fetcher",
  "environment": "production",
  "channel": "@ru_python",
  "date": "2025-11-02",
  "message_count": 370,
  "message": "Saved 370 messages"
}
```

### Retry attempt

```json
{
  "timestamp": "2025-11-03T10:31:12.789012+00:00",
  "level": "WARNING",
  "service": "telegram-fetcher",
  "function": "fetch_day",
  "error_type": "ConnectionError",
  "message": "Retrying in 2 seconds..."
}
```

### FloodWait

```json
{
  "timestamp": "2025-11-03T10:32:00.000000+00:00",
  "level": "WARNING",
  "service": "telegram-fetcher",
  "wait_seconds": 65,
  "message": "FloodWait encountered. Waiting 65 seconds..."
}
```

## 🔧 Troubleshooting

### Контейнер unhealthy

```bash
# Проверьте healthcheck файл
docker exec telegram-fetcher cat /tmp/.fetcher_healthy

# Проверьте логи
docker-compose -f docker-compose.fetcher.yml logs --tail=50 fetcher
```

### FloodWait слишком часто

Увеличьте REQUESTS_PER_SECOND:
```bash
REQUESTS_PER_SECOND=0.5  # Один запрос каждые 2 секунды
```

### VictoriaLogs не получает логи

```bash
# Проверьте connectivity
docker exec telegram-fetcher ping -c 3 victoria-logs

# Проверьте URL
docker exec telegram-fetcher env | grep VICTORIA

# Проверьте VictoriaLogs
curl http://localhost:9428/health
```

## 📈 Метрики и мониторинг

### Структурированные поля в логах

- `service` - имя сервиса
- `environment` - окружение (prod/dev/staging)
- `channel` - обрабатываемый канал
- `date` - дата обработки
- `message_count` - количество сообщений
- `error_type` - тип ошибки
- `wait_seconds` - время ожидания при FloodWait
- `processed` / `total` - прогресс обработки

### Запросы в VictoriaLogs

```bash
# Количество сообщений за сегодня
curl 'http://localhost:9428/select/logsql/query' -d 'query=_stream:{service="telegram-fetcher"} | stats sum(message_count)'

# Ошибки за последний час
curl 'http://localhost:9428/select/logsql/query' -d 'query=_stream:{service="telegram-fetcher"} level:ERROR _time:1h'

# Top каналы по сообщениям
curl 'http://localhost:9428/select/logsql/query' -d 'query=_stream:{service="telegram-fetcher"} | stats sum(message_count) by channel | sort by sum desc'
```

## 🚀 Production deployment

### Cron для ежедневного запуска

```cron
# Каждый день в 01:00
0 1 * * * cd /path/to/project && docker-compose -f docker-compose.fetcher.yml up fetcher >> /var/log/fetcher-cron.log 2>&1
```

### Systemd service

```ini
[Unit]
Description=Telegram Fetcher Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/docker-compose -f docker-compose.fetcher.yml up fetcher
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Systemd timer (альтернатива cron)

```ini
[Unit]
Description=Telegram Fetcher Timer

[Timer]
OnCalendar=daily
OnCalendar=01:00
Persistent=true

[Install]
WantedBy=timers.target
```

## 📝 Changelog MVP+

**Добавлено:**
- ✅ Structured JSON logging (python-json-logger)
- ✅ VictoriaLogs integration для централизованных логов
- ✅ Автоматический retry с exponential backoff (tenacity)
- ✅ FloodWait handling с автоматическим ожиданием
- ✅ Rate limiting для предотвращения FloodWait
- ✅ Graceful shutdown с сохранением прогресса
- ✅ Healthcheck для Docker
- ✅ Correlation ID для трассировки запросов
- ✅ Детальные метрики в логах

**Улучшено:**
- Обработка ошибок с контекстом
- Прогресс обработки с подсчётом каналов
- Логирование с дополнительными полями (channel, date, count)

## 🔜 Что дальше?

- [ ] Prometheus metrics для Grafana
- [ ] Error notifications в Telegram
- [ ] Параллелизация каналов
- [ ] Task queue integration
- [ ] Session pool для масштабирования
