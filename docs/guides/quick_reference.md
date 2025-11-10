# Quick Reference Guide

Краткая справка по командам и workflow.

## 🚀 Первый запуск (5 минут)

```bash
# Windows
.\scripts\quickstart.ps1

# Linux/Mac
chmod +x scripts/*.sh
./scripts/quickstart.sh
```

Затем:
1. Отредактировать `.env` с Telegram credentials
2. Перезапустить: `docker-compose restart telegram-fetcher`
3. Открыть Grafana: http://localhost:3000

## 📝 Повседневные команды

### Windows (PowerShell)

```powershell
# Запуск
.\scripts\dev.ps1 docker-up           # Запустить все сервисы
.\scripts\dev.ps1 docker-logs         # Смотреть логи
.\scripts\dev.ps1 docker-down         # Остановить

# Статус
.\scripts\status.ps1                  # Проверить состояние

# Локальная разработка
.\scripts\dev.ps1 run                 # Запустить локально
.\scripts\dev.ps1 test                # Тесты
.\scripts\dev.ps1 format              # Форматирование
```

### Linux/Mac (Bash)

```bash
# Запуск
./scripts/dev.sh docker-up            # Запустить все сервисы
./scripts/dev.sh docker-logs          # Смотреть логи
./scripts/dev.sh docker-down          # Остановить

# Статус
./scripts/status.sh                   # Проверить состояние

# Локальная разработка
./scripts/dev.sh run                  # Запустить локально
./scripts/dev.sh test                 # Тесты
./scripts/dev.sh format               # Форматирование
```

## 🔍 Мониторинг

### Логи в Loki (через Grafana)
```
1. http://localhost:3000
2. Explore → Loki
3. {service="telegram-fetcher"}
```

### Метрики в Prometheus
```
1. http://localhost:9090
2. Graph
3. up{job="telegram-fetcher"}
```

### Docker логи
```bash
# Все логи
docker-compose logs -f

# Только fetcher
docker-compose logs -f telegram-fetcher

# Последние 100 строк
docker-compose logs --tail=100 telegram-fetcher
```

## 📂 Структура данных

```
data/
  ├── @channel1/
  │   ├── 2025-11-05.json
  │   └── 2025-11-06.json
  └── @channel2/
      └── 2025-11-06.json

sessions/
  └── session_1234567890.session

progress.json
```

## ⚙️ Конфигурация

### Основные переменные `.env`
```env
# Обязательные
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef...
TELEGRAM_PHONE=+1234567890
TELEGRAM_CHATS=@channel1,@channel2

# Режим
FETCH_MODE=yesterday          # yesterday|full|incremental|date|range

# Для режима date
FETCH_DATE=2025-11-05

# Для режима range
FETCH_START=2025-11-01
FETCH_END=2025-11-05

# Логирование
LOG_LEVEL=INFO               # DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json              # json|text
```

### Автоматические (Docker)
```env
LOKI_URL=http://loki:3100
PUSHGATEWAY_URL=http://pushgateway:9091
```

## 🛠️ Troubleshooting

### Проблема: Не запускается
```bash
# Проверить Docker
docker --version
docker-compose --version

# Проверить порты
# Windows
netstat -an | findstr "3000 9090 3100 9091"
# Linux/Mac
netstat -an | grep -E "3000|9090|3100|9091"

# Пересоздать volumes
docker-compose down -v
docker volume create observability-stack_prometheus-data
docker volume create observability-stack_loki-data
docker volume create observability-stack_grafana-data
docker volume create observability-stack_pushgateway-data
docker-compose up -d --build
```

### Проблема: Authentication failed
```bash
# Удалить старые сессии
rm -rf sessions/*           # Linux/Mac
Remove-Item sessions\* -Force  # Windows

# Перезапустить с интерактивным вводом кода
docker-compose logs -f telegram-fetcher
# Ввести код из Telegram при запросе
```

### Проблема: No data in Grafana
```bash
# Проверить что Loki получает логи
curl http://localhost:3100/ready

# Проверить что fetcher пишет логи
docker-compose logs telegram-fetcher | head -20

# Проверить LOG_FORMAT=json в .env
```

### Проблема: Messages not fetching
```bash
# Проверить credentials в .env
cat .env | grep TELEGRAM_

# Проверить что каналы доступны
# (должны быть публичными или у вас должен быть доступ)

# Проверить логи на ошибки
docker-compose logs telegram-fetcher | grep -i error
```

## 🧹 Очистка

```bash
# Мягкая (остановить сервисы)
docker-compose down

# Жесткая (удалить volumes с данными)
# Windows
.\scripts\dev.ps1 docker-clean

# Linux/Mac
./scripts/dev.sh docker-clean

# Удалить только данные сообщений (оставить sessions)
rm -rf data/*
```

## 📊 Режимы работы

| Режим | Описание | Пример |
|-------|----------|---------|
| `yesterday` | Только вчерашний день | Ежедневный cron |
| `full` | Вся история до вчера | Первый запуск |
| `incremental` | С последней даты до сегодня | После паузы |
| `continuous` | Постоянный режим | Live monitoring |
| `date` | Конкретная дата | Backfill |
| `range` | Диапазон дат | Bulk fetch |

## 🔐 Безопасность

### Секреты
- ❌ Никогда не коммитить `.env`
- ✅ Использовать `.env.example` как шаблон
- ✅ Хранить credentials в secrets manager (production)

### Sessions
- Файлы `.session` содержат auth токены
- Не делиться ими
- Бэкапить безопасно

## 📚 Полезные ссылки

- [README.md](../README.md) - Полная документация
- [TZ](tech_task/TZ-telegram-fetcher.md) - Техническое задание
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Docker deployment guide
- [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) - Чеклист тестирования
- [PRE_IMPLEMENTATION_CHECKLIST.md](PRE_IMPLEMENTATION_CHECKLIST.md) - Чеклист перед разработкой

## 💡 Советы

1. **Начинайте с `yesterday` режима** - безопасно и быстро
2. **Используйте `./scripts/status` регулярно** - мониторинг состояния
3. **Бэкапьте `sessions/`** - чтобы не логиниться снова
4. **Проверяйте `progress.json`** - видите где остановились
5. **Мониторьте Grafana** - видите проблемы раньше
