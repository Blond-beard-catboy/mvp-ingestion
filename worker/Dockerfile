FROM python:3.11-slim AS builder

WORKDIR /app

# Копируем зависимости Worker
COPY worker/requirements.txt .
COPY api/requirements.txt ./api_requirements.txt

# Устанавливаем все зависимости
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user -r api_requirements.txt

# ===========================================
FROM python:3.11-slim

WORKDIR /app

# Копируем Python зависимости из builder
COPY --from=builder /root/.local /root/.local

# Копируем код проекта
COPY api/ ./api/
COPY worker/ ./worker/
COPY shared/ ./shared/
COPY .env.example .env

# Устанавливаем переменные окружения
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Запуск воркера
CMD ["python", "-m", "worker.worker"]