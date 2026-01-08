#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Остановка ВСЕГО проекта ==="
echo ""

docker-compose down

echo ""
echo "✅ Все сервисы остановлены"
echo ""
echo "Для полной очистки с удалением данных:"
echo "  docker-compose down -v"
echo ""
echo "Для удаления Docker образов:"
echo "  docker-compose down --rmi all"