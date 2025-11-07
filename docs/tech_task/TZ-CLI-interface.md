# TZ: CLI Interface для tg_fetcher

## Business Goal
Упростить использование fetcher через командную строку вместо редактирования `.env` файла.

## Current Problem
- Сейчас все параметры задаются через environment variables в `.env`
- Для изменения параметров нужно редактировать файл
- Невозможно быстро запустить с другими параметрами
- Пример: `python -m src.main --chat @ru_python --date 2025-11-05 --force-refetch` не работает

## Functional Requirements

### Must Have
1. CLI аргументы должны **переопределять** значения из `.env`
2. Основные параметры:
   - `--chat CHAT` - один чат для фетчинга (может быть несколько раз)
   - `--date YYYY-MM-DD` - конкретная дата
   - `--start YYYY-MM-DD --end YYYY-MM-DD` - диапазон дат
   - `--mode {yesterday,full,incremental,continuous,date,range}` - режим
   - `--force-refetch` - флаг принудительной перезагрузки
   - `--reset-progress` - сброс прогресса
3. Помощь: `--help` с описанием всех опций
4. Валидация аргументов
5. Обратная совместимость: если аргументы не переданы, используются значения из `.env`

### Nice to Have
1. `--list-chats` - показать все доступные чаты из конфига
2. `--status` - показать статус прогресса
3. `--verbose` / `--debug` - уровень логирования
4. `--config PATH` - альтернативный `.env` файл
5. Автодополнение (bash/zsh completion)

## Technical Decisions

### Library
**Click** - рекомендуется, т.к.:
- Простой и декларативный синтаксис
- Автоматическая генерация help
- Поддержка подкоманд (для будущего расширения)
- Хорошая валидация типов
- Широко используется в Python проектах

Альтернатива: `argparse` (stdlib, но более verbose)

### Implementation Strategy
1. Добавить `click` в `requirements.txt`
2. Создать `src/cli.py` с командами
3. Обновить `src/main.py`:
   ```python
   async def main(cli_args: dict | None = None) -> int:
       # Merge CLI args with env config
       config = FetcherConfig(**cli_args) if cli_args else FetcherConfig()
   ```
4. Обновить `src/__main__.py` для вызова CLI

### Priority Order (Highest to Lowest)
1. CLI аргументы (переданные явно)
2. Environment variables
3. `.env` файл
4. Default values в Pydantic модели

## API Design

### Примеры использования

```bash
# Fetch конкретного чата за вчера (по умолчанию)
python -m src --chat @ru_python

# Fetch за конкретную дату
python -m src --chat @ru_python --date 2025-11-05

# Fetch за диапазон дат
python -m src --chat @ru_python --start 2025-11-01 --end 2025-11-05

# Принудительная перезагрузка
python -m src --chat @ru_python --date 2025-11-05 --force-refetch

# Несколько чатов
python -m src --chat @ru_python --chat @pythonstepikchat

# Полная перезагрузка с нуля
python -m src --chat @ru_python --mode full --reset-progress

# Continuous режим
python -m src --chat @ru_python --mode continuous

# Помощь
python -m src --help
```

### Структура команд (Future)

```bash
# Основная команда - fetch (по умолчанию)
python -m src fetch --chat @ru_python --date 2025-11-05

# Подкоманды (future)
python -m src status                    # Show progress
python -m src list-chats                # List configured chats
python -m src reset --chat @ru_python   # Reset progress for chat
python -m src export --chat @ru_python --format csv  # Export data
```

## Implementation Plan

### Phase 1: Basic CLI (Immediate)
1. ✅ Установить `click`
2. Создать `src/cli.py` с основными опциями:
   - `--chat`
   - `--date`
   - `--start` / `--end`
   - `--force-refetch`
   - `--mode`
3. Обновить `src/main.py` для приема CLI параметров
4. Обновить `src/__main__.py`
5. Тестирование
6. Обновить документацию README.md

### Phase 2: Extended CLI (Future)
1. Добавить `--list-chats`, `--status`
2. Подкоманды (fetch, status, reset, export)
3. Автодополнение
4. Конфиг файлы (альтернатива .env)

## Testing

### Manual Test Cases
```bash
# TC1: Override chat from .env
python -m src --chat @test_chat

# TC2: Force refetch works
python -m src --chat @ru_python --date 2025-11-05 --force-refetch

# TC3: Date validation
python -m src --chat @ru_python --date invalid_date  # Should error

# TC4: Help works
python -m src --help

# TC5: No args uses .env
python -m src
```

### Automated Tests
- Unit tests для CLI argument parsing
- Integration tests для config merging
- Validation tests

## Status
- [ ] In Progress
- [ ] Implemented
- [ ] Tested
- [ ] Documented

## Notes
- Сейчас: все через `.env` → неудобно для быстрых тестов
- После: CLI args override .env → гибкость + удобство
- Обратная совместимость: старый способ через `.env` продолжит работать
