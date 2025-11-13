# Testing Checklist

Полный чеклист для тестирования интеграции перед production deployment.

## ✅ Pre-Testing Setup

- [ ] `.env` создан из `.env.example` и заполнен корректными credentials
- [ ] Docker и Docker Compose установлены и работают
- [ ] Git submodule observability-stack инициализирован
- [ ] Порты 3000, 3100, 9090, 9091 свободны

## 📦 Phase 1: Local Dependencies Test

```bash
# Windows
.\scripts\dev.ps1 install

# Linux/Mac
./scripts/dev.sh install
```

---

## 🔬 Quick Dev Checks (Unit/Integration)

### Unit tests

- Run all unit tests:
   - Windows PowerShell: `pytest -q tests\unit`

### Integration: Redis CommandSubscriber (Testcontainers)

- Requires Docker daemon running
- Run only these tests:
   - Windows PowerShell: `pytest -q tests\integration\test_command_subscriber.py`
- Tests will be skipped automatically if Docker is unavailable

## 🧮 Type Checking & Type Coverage

- Run mypy across sources:
   - Windows PowerShell: `py -m mypy src`
- Generate type coverage (line count) report into `typecov/`:
   - Windows PowerShell: `powershell -NoProfile -File scripts/type_coverage.ps1`
   - Open `typecov/index.txt` for per-module typed-line stats

**Проверить:**
- [ ] Все dependencies установлены без ошибок
- [ ] `pydantic>=2.0.0` установлен
- [ ] `python-logging-loki` установлен
- [ ] `telethon` установлен

## 🔧 Phase 2: Configuration Validation

```bash
# Windows
python -c "from src.core.config import FetcherConfig; config = FetcherConfig(); print('Config OK')"

# Linux/Mac
python -c "from src.core.config import FetcherConfig; config = FetcherConfig(); print('Config OK')"
```

**Проверить:**
- [ ] Config загружается без ValidationError
- [ ] TELEGRAM_API_ID валидируется корректно
- [ ] TELEGRAM_PHONE соответствует паттерну
- [ ] TELEGRAM_CHATS парсится в список

## 🐳 Phase 3: Docker Build Test

```bash
# Windows
.\scripts\dev.ps1 docker-build

# Linux/Mac
./scripts/dev.sh docker-build
```

**Проверить:**
- [ ] Multi-stage build завершается успешно
- [ ] Builder stage компилирует зависимости
- [ ] Runtime stage создан с non-root пользователем
- [ ] Image размер разумный (< 500MB)

## 🚀 Phase 4: Full Stack Deployment

```bash
# Windows
.\scripts\quickstart.ps1

# Linux/Mac
./scripts/quickstart.sh
```

**Проверить:**
- [ ] Volumes создаются
- [ ] docker-compose up завершается без ошибок
- [ ] Все 5 сервисов запускаются (fetcher, loki, prometheus, grafana, pushgateway)
- [ ] Health checks проходят

## 🌐 Phase 5: Services Accessibility

```bash
# Windows
.\scripts\status.ps1

# Linux/Mac
./scripts/status.sh
```

**Проверить доступность:**
- [ ] Grafana: http://localhost:3000 (login: admin/admin)
- [ ] Prometheus: http://localhost:9090
- [ ] Loki: http://localhost:3100/ready
- [ ] Pushgateway: http://localhost:9091

## 📊 Phase 6: Observability Integration

### Loki Logs
1. Открыть Grafana: http://localhost:3000
2. Go to Explore → Loki data source
3. Query: `{service="telegram-fetcher"}`

**Проверить:**
- [ ] Логи отображаются в Loki
- [ ] JSON format корректный
- [ ] correlation_id присутствует в логах
- [ ] Timestamp правильный

### Prometheus Metrics
1. Открыть Prometheus: http://localhost:9090
2. Go to Graph
3. Query: `up{job="telegram-fetcher"}`

**Проверить:**
- [ ] Метрики собираются
- [ ] Pushgateway доступен
- [ ] Scrape intervals работают

## 💬 Phase 7: Message Fetching Test

```bash
docker-compose logs -f telegram-fetcher
```

**Проверить:**
- [ ] Telegram authentication успешна (или запрашивает код)
- [ ] Channels/chats резолвятся
- [ ] Messages fetching начинается
- [ ] Нет ошибок в логах

## 💾 Phase 8: Data Persistence

**Проверить структуру данных:**
- [ ] `data/{source_name}/{YYYY-MM-DD}.json` создаются
- [ ] JSON файлы содержат `version: "1.0"`
- [ ] `source_info` заполнен корректно
- [ ] `senders` содержит mapping ID → name
- [ ] `messages` содержат все поля

**Проверить reactions extraction (если есть в сообщениях):**
- [ ] `reactions` массив содержит emoji и count
- [ ] Reaction models валидируются Pydantic

**Проверить comments extraction (если канал с discussion):**
- [ ] `comments` массив заполнен
- [ ] Nested Message models корректны

## 🔄 Phase 9: Progress Tracking

**Проверить:**
- [ ] `progress.json` создается
- [ ] `sources` содержит записи для каждого источника
- [ ] `last_processed_date` обновляется
- [ ] `completed_dates` заполняется

## 🛑 Phase 10: Graceful Shutdown

```bash
docker-compose down
```

**Проверить:**
- [ ] Все контейнеры останавливаются без ошибок
- [ ] Данные сохранены (data/, sessions/, progress.json)
- [ ] Volumes остаются (не удалены)

## 🔁 Phase 11: Resume Test

```bash
# Запустить снова
docker-compose up -d
```

**Проверить:**
- [ ] Sessions восстанавливаются (нет повторной аутентификации)
- [ ] Progress загружается из progress.json
- [ ] Fetching продолжается с правильного места

## ⚠️ Phase 12: Error Handling

**Симулировать ошибки:**

1. **Неверные credentials:**
   - Изменить TELEGRAM_API_ID на неверный
   - Перезапустить
   - **Проверить:** Логируется понятная ошибка

2. **Network timeout:**
   - Остановить Loki: `docker-compose stop loki`
   - **Проверить:** Fetcher продолжает работать, логи в stdout

3. **Несуществующий канал:**
   - Добавить @nonexistent_channel_12345 в TELEGRAM_CHATS
   - **Проверить:** Ошибка логируется, но другие каналы обрабатываются

## 📈 Phase 13: Performance Check

```bash
docker stats
```

**Проверить:**
- [ ] Memory usage < 500MB для fetcher
- [ ] CPU usage разумный
- [ ] No memory leaks (usage стабильный)

## 🧹 Phase 14: Cleanup Test

```bash
# Windows
.\scripts\dev.ps1 docker-clean

# Linux/Mac
./scripts/dev.sh docker-clean
```

**Проверить:**
- [ ] Все контейнеры удалены
- [ ] Volumes удалены
- [ ] Images опционально удалены

## ✅ Final Checklist

### Готов к production если:
- [ ] Все фазы пройдены успешно
- [ ] Логи читаемые и информативные
- [ ] Метрики собираются корректно
- [ ] Данные сохраняются в правильном формате
- [ ] Resume работает после перезапуска
- [ ] Error handling корректный
- [ ] Performance приемлемый

### Документация проверена:
- [ ] README.md актуален
- [ ] DOCKER_DEPLOYMENT.md корректен
- [ ] Scripts работают как описано
- [ ] .env.example содержит все переменные

## 🐛 Known Issues / Notes

_Добавить сюда найденные проблемы или заметки при тестировании_

---

**Tested by:** _______________
**Date:** _______________
**Environment:** Windows / Linux / Mac
**Result:** ✅ Pass / ❌ Fail
