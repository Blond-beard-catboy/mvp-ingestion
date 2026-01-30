#!/bin/bash
set -e

echo "=== Running Alembic migrations ==="

POSTGRES_URL=${POSTGRES_URL:-postgresql://events_user:password@postgres:5432/events_db}
echo "Database URL: $POSTGRES_URL"

# Парсим хост и порт из URL
DB_HOST=$(echo $POSTGRES_URL | sed -n 's/.*@\([^:/]*\).*/\1/p')
DB_PORT=$(echo $POSTGRES_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
if [ -z "$DB_PORT" ]; then
    DB_PORT=5432
fi

echo "Host: $DB_HOST, Port: $DB_PORT"

# Ждем доступности PostgreSQL
echo -n "Waiting for PostgreSQL to be ready..."
timeout=60
while ! nc -z $DB_HOST $DB_PORT; do
    timeout=$((timeout-1))
    if [ $timeout -le 0 ]; then
        echo ""
        echo "ERROR: PostgreSQL is not available after 60 seconds"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""
echo "✅ PostgreSQL is ready"

# Применяем миграции
echo "Running Alembic migrations..."
cd /app/migrations
alembic upgrade head

echo "✅ Migrations completed successfully"
