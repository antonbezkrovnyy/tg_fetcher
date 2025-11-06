FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY services/fetcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование observability модуля
COPY observability /app/observability

# Копирование исходного кода
COPY services/fetcher/fetcher.py .
COPY services/fetcher/fetch_yesterday.py .
COPY services/fetcher/fetcher_utils.py .
COPY services/fetcher/retry_utils.py .
COPY services/fetcher/shutdown_utils.py .
COPY services/fetcher/healthcheck.py .
COPY services/fetcher/entrypoint.sh .

# Создание директорий для данных и логов
RUN mkdir -p /data/channels /data/chats /sessions /var/log /tmp

# Делаем entrypoint исполняемым
RUN chmod +x entrypoint.sh

# Healthcheck - проверка каждые 30 секунд
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /app/healthcheck.py 2>/dev/null || exit 1

# Entrypoint для выбора режима работы
ENTRYPOINT ["/app/entrypoint.sh"]
