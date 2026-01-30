FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код API
COPY api/ /app/api/
COPY shared/ /app/shared/

# Копируем миграции Alembic
COPY migrations/ /app/migrations/

# Копируем скрипты
COPY scripts/run_migrations.sh /app/scripts/

# Создаем папку для логов
RUN mkdir -p /app/logs

# Делаем скрипты исполняемыми
RUN chmod +x /app/scripts/run_migrations.sh

# Переменные окружения по умолчанию
ENV PYTHONPATH=/app
ENV FLASK_APP=/app/api/app.py
ENV FLASK_ENV=production

# Запускаем миграции и API
CMD ["sh", "-c", "/app/scripts/run_migrations.sh && python /app/api/app.py"]

EXPOSE 5000