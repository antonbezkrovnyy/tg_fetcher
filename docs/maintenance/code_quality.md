# Code Quality Tools

## Main Tools

### 1. Code Formatters

#### black
- **Конфиг**: `pyproject.toml` → `[tool.black]`
- **Длина строки**: 88 символов
- **Проверка**: `black --check .`
- **Применение**: `black .`

#### isort
- **Конфиг**: `pyproject.toml` → `[tool.isort]`
- **Профиль**: black-compatible
- **Проверка**: `isort --check-only .`
- **Применение**: `isort .`

### 2. Linters

#### flake8
- **Конфиг**: `.flake8`
- **Длина строки**: 88 (как в black)
- **Игнор**: `E203, W503` (конфликты с black)
- **Проверка**: `flake8`

#### mypy
- **Конфиг**: `pyproject.toml` → `[tool.mypy]`
- **Строгость**: High
- **Проверка**: `mypy src/`

## Quick Commands

### Check Everything
```bash
# Format and check
black . && isort . && flake8 && mypy src/
```

### Pre-commit
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Style Guide

### Code Style
- Black форматирование
- Google style docstrings
- Типы для всех функций
- Не более 88 символов в строке

### Imports Style
1. Standard library
2. Third party
3. Local modules

### Docstrings
```python
def function(param: str) -> bool:
    """Short description.

    Args:
        param: Parameter description

    Returns:
        Description of return value

    Raises:
        ValueError: When param is invalid
    """
```

### Type Hints
```python
# Yes
def process(items: list[str]) -> dict[str, int]:

# No
def process(items):
```

## Common Issues

### Black vs Flake8
- Используем black длину (88)
- Игнорируем конфликтующие правила
- Black всегда приоритетнее

### Long Lines
- Используйте скобки
- Разбивайте параметры
- f-строки на несколько строк

### Type Hints
- Union = X | Y (Python 3.10+)
- Optional = None | X
- Annotated для валидации