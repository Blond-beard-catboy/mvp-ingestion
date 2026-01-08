#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Запуск ВСЕГО проекта в Docker Compose ==="
echo "Сервисы: RabbitMQ, PostgreSQL, MySQL, API, Worker"
echo ""

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Ошибка: docker-compose не найден"
    exit 1
fi

# Останавливаем предыдущие контейнеры
echo "Останавливаем предыдущие контейнеры..."
docker-compose down

# Собираем и запускаем все сервисы
echo "Сборка и запуск контейнеров..."
docker-compose up --build -d

echo ""
echo "⏳ Ожидание запуска сервисов (30 секунд)..."
sleep 30

echo ""
echo "✅ Все сервисы запущены:"
echo ""
echo "1. RabbitMQ:"
echo "   - AMQP:        amqp://localhost:5672"
echo "   - Web UI:      http://localhost:15672 (guest/guest)"
echo ""
echo "2. Базы данных:"
echo "   - PostgreSQL:  localhost:5432 (events_user/password)"
echo "   - MySQL:       localhost:3306 (events_user/password)"
echo ""
echo "3. Приложения:"
echo "   - API:         http://localhost:5000"
echo "   - Worker:      (работает в фоне)"
echo ""
echo "Команды для управления:"
echo "   Просмотр логов:    docker-compose logs -f"
echo "   Остановка:         docker-compose down"
echo "   Перезапуск API:    docker-compose restart api"
echo "   Перезапуск Worker: docker-compose restart worker"
echo ""
echo "Проверка здоровья:"
curl -s http://localhost:5000/health | python3 -m json.tool || echo "API еще не готов"