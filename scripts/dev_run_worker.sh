#!/bin/bash

# Скрипт для запуска воркера в development-режиме

set -e  # Выход при ошибке

echo "=== Starting Event Worker ==="

# Переходим в корень проекта
cd "$(dirname "$0")/.."

# Активируем виртуальное окружение если оно существует
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Copy .env.example to .env and adjust values"
    exit 1
fi

# Проверяем наличие RabbitMQ
echo "Checking RabbitMQ..."
if ! curl -s http://localhost:15672 > /dev/null 2>&1; then
    echo "⚠️  Warning: RabbitMQ management interface not reachable"
    echo "   Make sure RabbitMQ is running: docker start rabbitmq"
fi

# Проверяем наличие PostgreSQL
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  Warning: psql not found, PostgreSQL client not installed"
fi

# Устанавливаем зависимости воркера
echo "Installing worker dependencies..."
pip install -r worker/requirements.txt

# Запускаем воркер
echo ""
echo "Starting worker with configuration:"
echo "  RabbitMQ: ${RABBIT_URL:-amqp://guest:guest@localhost:5672/}"
echo "  PostgreSQL: ${POSTGRES_URL:-not set}"
echo "  Log level: ${LOG_LEVEL:-INFO}"
echo ""
echo "Press Ctrl+C to stop"
echo "========================"

cd worker
python worker.py