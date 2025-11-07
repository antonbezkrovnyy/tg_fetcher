---
applyTo: '**'
---

# 🚨 CRITICAL AI AGENT RULES - ALWAYS ACTIVE

## Before ANY Response - Mandatory Checklist

**YOU MUST check these BEFORE responding:**

```
□ Did I read the FULL user request?
□ Do I need to check PRE_IMPLEMENTATION_CHECKLIST.md?
□ Should I ask clarifying questions FIRST?
□ Am I about to write code without a plan? STOP!
□ Did I batch ALL questions together?
□ Will I log terminal commands to console.log?
□ Am I using the user's communication language?
```

## 🔴 NEVER Do This (Red Flags)

1. **❌ NEVER write code immediately** without:
   - Asking clarifying questions
   - Creating/updating Technical Specification (TZ)
   - Getting user confirmation on approach

2. **❌ NEVER ask questions sequentially**
   - ❌ Bad: "What database?" → user answers → "What authentication?" → user answers
   - ✅ Good: "What database? What authentication? What API design?" → user answers once

3. **❌ NEVER forget to log commands**
   - Every `run_in_terminal` → MUST update `docs/console.log`
   - Format: `[YYYY-MM-DD HH:MM:SS Category] command - description`

4. **❌ NEVER skip type hints or docstrings**
   - Every function MUST have type annotations
   - Every public function MUST have Google-style docstring

5. **❌ NEVER make assumptions**
   - Don't know? ASK!
   - Multiple interpretations? ASK ALL!
   - Unclear requirement? ASK BEFORE CODING!

## ✅ ALWAYS Do This (Golden Rules)

### 1. **Communication Flow**
```
User Request → Clarify → Plan → Confirm → Execute → Document
```

Never skip steps!

### 2. **Question Batching Template**
```markdown
## 🤔 Уточняющие вопросы (нужно ответить перед началом):

1. **[Category 1]**: Question about X?
2. **[Category 2]**: Question about Y?
3. **[Category 3]**: Question about Z?

## 📋 Предлагаемый подход:

После получения ответов я:
1. Step 1
2. Step 2
3. Step 3

**Подходит? Мне начинать?**
```

### 3. **Technical Specification (TZ) First**
For ANY new feature:
```
1. Create docs/tech_task/TZ-<feature>.md
2. Fill sections: Goal, Requirements, Architecture, API
3. Get user approval
4. Then and ONLY then start coding
```

### 4. **Code Quality Gates**
Every code change MUST have:
```python
def function_name(param: str) -> dict[str, Any]:  # ✅ Type hints
    """Short description.                         # ✅ Docstring

    Args:
        param: What it is

    Returns:
        What it returns

    Raises:
        ValueError: When...
    """
    if not param:                                  # ✅ Validation
        raise ValueError("param is required")

    logger.info("Action", extra={"param": param})  # ✅ Logging
    return {"result": param}
```

### 5. **Command Logging**
```
[2025-11-06 14:30:00 Docker] docker-compose up --build - Building telegram-fetcher
[2025-11-06 14:31:00 Git] git commit -m "feat: add feature" - Committing changes
[2025-11-06 14:32:00 Testing] pytest tests/ - Running tests

Categories: Testing, Environment, Dependencies, Docker, Git, QA, Code, Documentation, Config
```

## 🎯 Workflows by Task Type

### 🆕 New Feature Request
```
1. ASK: Clarifying questions (database? auth? API design?)
2. CREATE: docs/tech_task/TZ-<name>.md
3. DISCUSS: Architecture, approach
4. CONFIRM: "Should I proceed with this plan?"
5. CHECK: docs/PRE_IMPLEMENTATION_CHECKLIST.md
6. IMPLEMENT: Incrementally (small pieces)
7. TEST: Write/run tests
8. DOCUMENT: Update docs, update TZ
9. LOG: All commands to console.log
10. COMMIT: With conventional commit message
```

### 🐛 Bug Fix
```
1. ASK: "Can you provide: error logs, steps to reproduce, expected vs actual?"
2. ANALYZE: Read code, understand root cause
3. EXPLAIN: "The bug is caused by X because Y"
4. PROPOSE: "I suggest fixing by doing Z"
5. CONFIRM: "Should I proceed?"
6. FIX: Implement solution
7. TEST: Verify fix works
8. LOG: Commands
9. COMMIT: fix: description
```

### 📝 Documentation
```
1. ASK: "What specifically should I document? Target audience?"
2. OUTLINE: Present structure
3. CONFIRM: "Does this structure work?"
4. WRITE: Create documentation (in user's language)
5. REVIEW: Check completeness
6. COMMIT: docs: description
```

### 🔧 Refactoring
```
1. ASK: "Why refactor? What's the problem with current code?"
2. ANALYZE: Understand current implementation
3. PROPOSE: "I suggest refactoring to pattern X because Y"
4. CONFIRM: "Proceed?"
5. REFACTOR: Maintain tests, backward compatibility
6. TEST: Ensure all tests pass
7. COMMIT: refactor: description
```

### 🧪 Testing
```
1. ASK: "What should be tested? Unit/integration?"
2. PLAN: Test cases
3. WRITE: Tests with good coverage
4. RUN: Verify they pass
5. DOCUMENT: Add to testing docs
```

## 🚦 Decision Tree

```
User Request
    ↓
Is it a question?
    YES → Answer directly
    NO → Is it about code?
        YES → Need to write code?
            YES → 🚨 STOP!
                  1. Ask questions
                  2. Create TZ
                  3. Get approval
                  4. Then code
            NO → Just explain/review
        NO → Handle appropriately
```

## 📚 Examples: Good vs Bad

### Example 1: Feature Request

❌ **BAD Response:**
```
User: "Добавь JWT аутентификацию"
AI: *creates auth.py, jwt_utils.py, user_model.py immediately*
```

✅ **GOOD Response:**
```
User: "Добавь JWT аутентификацию"

AI: "## 🤔 Уточняющие вопросы:

1. **База данных**: Где хранить пользователей? (PostgreSQL/MongoDB/SQLite?)
2. **Хэширование**: Какой алгоритм? (bcrypt/argon2?)
3. **Токены**: Срок действия? Refresh tokens нужны?
4. **Endpoints**: Какие нужны? (register, login, refresh, logout?)
5. **Middleware**: На все routes или выборочно?

## 📋 Предлагаемая структура:

После ответов создам:
- docs/tech_task/TZ-jwt-authentication.md (техническое задание)
- Обсудим архитектуру
- Реализуем по частям

**Подходит?**"
```

### Example 2: Bug Report

❌ **BAD Response:**
```
User: "Не работает fetch"
AI: *changes code randomly hoping to fix*
```

✅ **GOOD Response:**
```
User: "Не работает fetch"

AI: "## 🤔 Уточняющие вопросы:

1. **Что именно не работает?** (ошибка, зависание, неверные данные?)
2. **Есть ли логи/ошибки?** Можете прислать?
3. **Шаги воспроизведения?** Как вызвать проблему?
4. **Ожидаемое поведение?** Что должно было произойти?
5. **Окружение?** (Docker/local, какая версия?)

После получения информации я:
1. Проанализирую логи
2. Найду root cause
3. Предложу решение
4. Жду вашего подтверждения перед исправлением

**Можете предоставить эту информацию?**"
```

### Example 3: Refactoring

❌ **BAD Response:**
```
User: "Улучши этот код"
AI: *refactors entire codebase without explanation*
```

✅ **GOOD Response:**
```
User: "Улучши этот код"

AI: "## 🤔 Уточняющие вопросы:

1. **Что конкретно не нравится?** (читаемость, производительность, структура?)
2. **Есть ли проблемы?** (баги, медленно работает?)
3. **Backward compatibility?** Нужна совместимость со старым API?
4. **Тесты есть?** Нужно сохранить поведение?

## 📋 Что я вижу сейчас:

- [Проблема 1]: Описание
- [Проблема 2]: Описание

## 💡 Предлагаемые улучшения:

1. [Улучшение 1]: Описание, почему лучше
2. [Улучшение 2]: Описание, почему лучше

**Какие улучшения применить?**"
```

## 🎓 Lessons Learned from This Project

### Mistake 1: Immediate Coding
**What happened:** AI started fixing bugs without asking about root cause
**Lesson:** ALWAYS ask for logs, reproduction steps, expected behavior FIRST
**Rule:** No code until problem is fully understood

### Mistake 2: Sequential Questions
**What happened:** Asked "What database?" → got answer → asked "What auth?" → got answer
**Lesson:** Batch ALL questions in one message
**Rule:** One comprehensive question message, not chat ping-pong

### Mistake 3: No TZ for Features
**What happened:** Implemented features without documenting requirements
**Lesson:** Create TZ first, update it with each clarification
**Rule:** `docs/tech_task/TZ-<name>.md` before first line of code

### Mistake 4: Forgot console.log
**What happened:** Ran many terminal commands but didn't log them
**Lesson:** Documentation suffers, hard to reproduce later
**Rule:** EVERY `run_in_terminal` → append to `docs/console.log` immediately

### Mistake 5: Missing Type Hints
**What happened:** Code worked but had no type annotations
**Lesson:** Harder to maintain, no IDE support, mypy fails
**Rule:** Type hints and docstrings are NOT optional

## 🔧 Tools Usage Rules

### When to use semantic_search
- ✅ Finding functionality across large codebase
- ✅ Don't know exact file/function name
- ✅ Searching by concept/behavior
- ❌ When you already know the file (use read_file)

### When to use grep_search
- ✅ Exact string/pattern known
- ✅ Finding all occurrences
- ✅ Quick overview of file contents
- ❌ Conceptual search (use semantic_search)

### When to use read_file
- ✅ Need to read specific code
- ✅ File already identified
- ✅ Read large meaningful chunks (50-100 lines)
- ❌ Reading entire 1000-line file at once

### When to create TZ
- ✅ Any new feature request
- ✅ Complex bug requiring architectural changes
- ✅ Refactoring affecting multiple files
- ❌ Simple typo fix or one-line change

## 🎯 Success Metrics

After following these rules, you should achieve:
- ✅ 100% type hint coverage
- ✅ 100% docstring coverage
- ✅ 0 mypy errors
- ✅ 0 flake8 violations
- ✅ Complete TZ for all features
- ✅ Full command history in console.log
- ✅ Happy user (fewer iterations, clearer communication)

## 🔄 Self-Check Before Responding

Ask yourself:
1. Did I understand the FULL request?
2. Do I need more information? → ASK NOW (batch all questions)
3. Am I about to code? → Do I have TZ? → Do I have approval? → No? STOP!
4. Am I using user's language for communication?
5. Will this require terminal commands? → Will I log them?
6. Does my code have type hints + docstrings?
7. Am I following project conventions?

If ANY answer is "No" or "Unsure" → FIX BEFORE PROCEEDING!

---

## 💡 Remember

**Quality > Speed**

It's better to:
- Ask 10 questions upfront
- Create thorough TZ
- Get clear approval
- Write clean code once

Than to:
- Make assumptions
- Write code immediately
- Iterate 5 times fixing misunderstandings
- End up with technical debt

**The user will appreciate:**
- ✅ Thoughtful questions
- ✅ Clear communication
- ✅ Well-structured code
- ✅ Comprehensive documentation

**The user will NOT appreciate:**
- ❌ Code that doesn't match requirements
- ❌ Multiple rounds of fixes
- ❌ Undocumented assumptions
- ❌ Missing type hints/docs
