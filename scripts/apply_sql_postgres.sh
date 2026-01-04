#!/bin/bash

# Скрипт для применения SQL схемы к PostgreSQL

set -e  # Выход при ошибке

echo "=== Applying PostgreSQL schema ==="

# Переходим в корень проекта
cd "$(dirname "$0")/.."

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Copy .env.example to .env and set POSTGRES_URL"
    exit 1
fi

# Загружаем переменные окружения
export $(grep -v '^#' .env | xargs)

# Проверяем наличие POSTGRES_URL
if [ -z "$POSTGRES_URL" ]; then
    echo "Error: POSTGRES_URL is not set in .env"
    exit 1
fi

# Извлекаем параметры подключения из URL
DB_USER=$(echo $POSTGRES_URL | sed -n 's/.*:\/\/\([^:]*\).*/\1/p')
DB_PASS=$(echo $POSTGRES_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\).*/\1/p')
DB_HOST=$(echo $POSTGRES_URL | sed -n 's/.*@\([^:/]*\).*/\1/p')
DB_PORT=$(echo $POSTGRES_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $POSTGRES_URL | sed -n 's/.*\/\([^/?]*\).*/\1/p')

# Устанавливаем стандартный порт если не указан
DB_PORT=${DB_PORT:-5432}

echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "User: $DB_USER"

# Проверяем наличие psql
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Install PostgreSQL client."
    exit 1
fi

# Применяем SQL схему
echo "Applying sql/setup_postgres.sql..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f sql/setup_postgres.sql

echo ""
echo "✅ PostgreSQL schema applied successfully!"
echo ""
echo "You can verify with:"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\dt'"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\d events'"