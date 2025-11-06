# Pre-Implementation Checklist

**ОБЯЗАТЕЛЬНО проверять ПЕРЕД началом любой реализации!**

## 1. Проверка соответствия copilot-instructions.md

### Библиотеки и фреймворки
- [ ] **Pydantic** - используется для валидации данных? (Data Validation section)
- [ ] **Observability-stack** - интегрирован для логов и метрик? (Python Environment section)
- [ ] **pytest** - настроен для тестирования с правильными маркерами?
- [ ] **black + isort** - используется для форматирования?
- [ ] **Type hints** - добавлены для всех функций?

### Архитектурные паттерны
- [ ] **SOLID principles** - соблюдены (особенно Single Responsibility)?
- [ ] **Repository pattern** - для доступа к данным?
- [ ] **Service layer** - для бизнес-логики?
- [ ] **Strategy pattern** - для вариативного поведения?
- [ ] **Dependency Inversion** - зависимость от абстракций?

### Workflow Rules
- [ ] **Создана/обновлена TZ** перед началом?
- [ ] **Задал все вопросы сразу**, а не по одному?
- [ ] **Получил подтверждение** перед генерацией кода?
- [ ] **Incremental approach** - маленькие части кода, не большие блоки?
- [ ] **Study references** - изучены примеры из docs/examples/?

## 2. Проверка соответствия TZ

### Технические решения из TZ
- [ ] **Database** - соответствует выбору из TZ?
- [ ] **External APIs** - все интеграции учтены?
- [ ] **Data Schema** - соответствует версионируемой схеме из TZ?
- [ ] **Progress tracking** - реализован механизм из TZ?
- [ ] **Error handling** - соответствует стратегии из TZ?

### Functional Requirements
- [ ] Все функциональные требования из TZ учтены?
- [ ] Все режимы работы реализованы/запланированы?
- [ ] Все форматы данных соответствуют TZ?

## 3. Проверка Project Structure

- [ ] Все необходимые директории созданы?
- [ ] `__init__.py` файлы на месте?
- [ ] **Dockerfile** создан?
- [ ] **docker-compose.yml** создан?
- [ ] **.env.example** с полным набором переменных?
- [ ] **pyproject.toml** настроен (если нужен)?

## 4. Dependencies Check

- [ ] **requirements.txt** - все production зависимости?
- [ ] **requirements-dev.txt** - все dev-зависимости?
- [ ] **Pydantic** в requirements.txt?
- [ ] **Observability handlers** (если нужны) добавлены?
- [ ] Версии зависимостей корректны (>= для гибкости)?

## 5. Observability Integration

- [ ] **observability-stack** - клонирован и запущен?
- [ ] **Logging handlers** - настроены для отправки в Loki?
- [ ] **Metrics exporters** - настроены для Prometheus?
- [ ] **Correlation IDs** - добавлены для трейсинга?
- [ ] **Structured logging** - JSON формат с правильными полями?

## 6. Code Quality

- [ ] **Type hints** на всех функциях?
- [ ] **Docstrings** (Google-style) для публичных функций?
- [ ] **Error handling** - специфичные исключения, не generic?
- [ ] **Logging** вместо print()?
- [ ] **No hardcoded secrets**?

## 7. Testing Strategy

- [ ] **Test files** созданы параллельно с кодом?
- [ ] **Fixtures** в conftest.py?
- [ ] **Mocking** для external dependencies?
- [ ] **Coverage** будет >80%?

## 8. Git & Documentation

- [ ] **console.log** будет обновлен с командами?
- [ ] **Commit messages** - conventional commits format?
- [ ] **README** обновлен (если нужно)?

## 9. Communication Checklist

- [ ] **Все вопросы заданы сразу** (batch questions)?
- [ ] **План согласован** с пользователем?
- [ ] **Scope подтвержден** перед реализацией?
- [ ] **Decisions документированы** в copilot-instructions.md?

---

## Quick Pre-Start Questions Template

Перед началом реализации задать:

```
Перед началом реализации уточним:

### Архитектура
1. Pydantic используем для валидации? (из copilot-instructions.md)
2. Observability-stack нужно интегрировать сейчас или позже?
3. Docker контейнеризация в этой фазе или отложить?

### Зависимости
4. Какие библиотеки еще нужны кроме [список из TZ]?
5. Нужны ли дополнительные handlers для логирования?

### Scope
6. Реализуем минимальный MVP или полную фичу?
7. Какие части можно отложить на следующую фазу?

### Валидация
8. Проверил checklist - всё учтено из copilot-instructions.md и TZ?
```

---

## Использование этого чеклиста

**ОБЯЗАТЕЛЬНО:**
1. Прочитать этот файл ПЕРЕД любой реализацией
2. Отметить все пункты чеклиста
3. Задать вопросы если хоть один пункт не ясен
4. Получить подтверждение плана
5. ТОЛЬКО ПОТОМ начинать писать код

**Цель:** Избежать ситуаций "упустил важную деталь из инструкций/TZ"
