FROM python:3.11-slim AS builder

WORKDIR /app

# Копируем зависимости API
COPY api/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --user -r requirements.txt

# ===========================================
FROM python:3.11-slim

WORKDIR /app

# Копируем Python зависимости из builder
COPY --from=builder /root/.local /root/.local

# Копируем код проекта
COPY api/ ./api/
COPY shared/ ./shared/
COPY .env.example .env

# Устанавливаем переменные окружения
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV FLASK_APP=api.app
ENV FLASK_ENV=production

# Порт API
EXPOSE 5000

# Запуск приложения
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]