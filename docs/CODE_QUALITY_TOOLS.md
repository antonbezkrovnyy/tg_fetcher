# Code Quality Tools

Этот проект использует автоматизированные инструменты для поддержания качества кода.

## Установленные инструменты

### 1. **black** - Автоформатирование кода
- **Настройка**: `pyproject.toml` → `[tool.black]`
- **Длина строки**: 88 символов
- **Запуск вручную**:
  ```bash
  black src/
  black --check src/  # проверка без изменений
  ```

### 2. **isort** - Сортировка импортов
- **Настройка**: `pyproject.toml` → `[tool.isort]`
- **Профиль**: `black` (совместимость с black)
- **Запуск вручную**:
  ```bash
  isort src/
  isort --check-only src/  # проверка без изменений
  ```

### 3. **flake8** - Линтер и проверка стиля
- **Настройка**: `.flake8`
- **Проверки**:
  - Стиль кода (PEP 8)
  - Docstrings (Google style)
  - Сложность функций (max 10)
  - Неиспользуемые импорты
- **Запуск вручную**:
  ```bash
  flake8 src/
  ```

### 4. **mypy** - Статическая проверка типов
- **Настройка**: `pyproject.toml` → `[tool.mypy]`
- **Строгость**: High (disallow_untyped_defs, strict_equality, etc.)
- **Плагины**: pydantic.mypy для поддержки Pydantic моделей
- **Запуск вручную**:
  ```bash
  mypy src/
  ```

### 5. **pre-commit** - Автоматические проверки перед коммитом
- **Настройка**: `.pre-commit-config.yaml`
- **Hooks**:
  - trailing-whitespace
  - end-of-file-fixer
  - check-yaml, check-toml, check-json
  - mixed-line-ending (LF)
  - black, isort, flake8, mypy
- **Установка**:
  ```bash
  pre-commit install
  ```
- **Запуск вручную**:
  ```bash
  pre-commit run --all-files
  ```

## Что проверяется

### Включено в проверки:
- ✅ `src/**/*.py` - основной код проекта
- ✅ `pyproject.toml`, `docker-compose.yml`, `.yaml` файлы

### Исключено из проверок:
- ❌ `tests/` - тестовый код (пока что)
- ❌ `migrations/` - миграции БД
- ❌ `.venv/` - виртуальное окружение
- ❌ `docs/examples/` - примеры и референсы
- ❌ `scripts/` - вспомогательные скрипты

## Рабочий процесс

### При разработке:

1. **Пишите код** как обычно
2. **Перед коммитом** автоматически запускаются все проверки
3. **Если ошибки** - pre-commit отклонит коммит:
   - Форматирование (black, isort) исправляется автоматически
   - Линтер (flake8) и типы (mypy) требуют ручного исправления
4. **После исправления** повторите `git commit`

### Обход pre-commit (для срочных случаев):
```bash
git commit --no-verify -m "ваше сообщение"
```
⚠️ **Внимание**: Используйте только в крайнем случае!

### Ручная проверка всех файлов:
```bash
# Все проверки сразу
pre-commit run --all-files

# Отдельно каждый инструмент
black --check src/
isort --check-only src/
flake8 src/
mypy src/
```

## Исправление ошибок

### black/isort - автоматически исправляются:
```bash
black src/
isort src/
git add -u
```

### flake8 - типичные ошибки:

**E501: line too long**
```python
# До:
logger.info("Очень длинное сообщение которое превышает 88 символов и нужно разбить")

# После:
logger.info(
    "Очень длинное сообщение которое превышает "
    "88 символов и нужно разбить"
)
```

**F401: imported but unused**
```python
# Удалите неиспользуемый импорт
from typing import Optional, Any  # Если Any не используется - уберите
```

**D415: First line should end with a period**
```python
# До:
"""This is a docstring"""

# После:
"""This is a docstring."""
```

### mypy - типичные ошибки:

**no-untyped-def**
```python
# До:
def process_data(data):
    return data

# После:
def process_data(data: dict[str, Any]) -> dict[str, Any]:
    return data
```

**Missing return type**
```python
# До:
async def fetch_messages(client):
    ...

# После:
async def fetch_messages(client: TelegramClient) -> list[Message]:
    ...
```

## CI/CD Integration (будущее)

Когда будет настроен GitHub Actions:
```yaml
- name: Run code quality checks
  run: |
    black --check src/
    isort --check-only src/
    flake8 src/
    mypy src/
```

## Конфигурационные файлы

- `.flake8` - настройки flake8
- `.pre-commit-config.yaml` - настройки pre-commit hooks
- `pyproject.toml` - настройки black, isort, mypy
- `requirements-dev.txt` - dev-зависимости с версиями

## Полезные команды

```bash
# Обновить pre-commit hooks до последних версий
pre-commit autoupdate

# Очистить кэш pre-commit
pre-commit clean

# Запустить конкретный hook
pre-commit run black --all-files

# Проверить один файл
black --check src/main.py
flake8 src/main.py
mypy src/main.py
```

## Метрики качества

По состоянию на 2025-11-06:

| Метрика | Значение |
|---------|----------|
| Type hints coverage | 100% |
| Docstrings coverage | 100% |
| Flake8 violations | 0 |
| Mypy errors | 0 |
| Black compliance | 100% |
| **Overall Score** | 10/10 |

## Troubleshooting

### Pre-commit не запускается
```bash
# Переустановите hooks
pre-commit uninstall
pre-commit install
```

### Mypy не видит Pydantic
```bash
# Установите pydantic plugin
pip install "pydantic[mypy]"
```

### Конфликты между black и flake8
- Уже настроено в `.flake8`: игнорируются E203, W503
- Эти правила несовместимы с black

## Ресурсы

- [Black documentation](https://black.readthedocs.io/)
- [isort documentation](https://pycqa.github.io/isort/)
- [flake8 documentation](https://flake8.pycqa.org/)
- [mypy documentation](https://mypy.readthedocs.io/)
- [pre-commit documentation](https://pre-commit.com/)
