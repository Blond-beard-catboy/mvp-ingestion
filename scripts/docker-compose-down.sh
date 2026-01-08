#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Остановка Docker Compose сервисов ==="
echo ""

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Ошибка: docker-compose не найден"
    exit 1
fi

docker-compose down

echo ""
echo "Сервисы остановлены"
echo "Для полной очистки с удалением данных: docker-compose down -v"