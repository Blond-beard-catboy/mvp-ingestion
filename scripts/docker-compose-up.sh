#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Запуск Docker Compose сервисов ==="
echo "Сервисы: RabbitMQ, PostgreSQL, MySQL"
echo ""

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Ошибка: docker-compose не найден"
    exit 1
fi

# Запускаем сервисы в фоновом режиме
docker-compose up -d

echo ""
echo "Сервисы запущены:"
echo "  RabbitMQ:      amqp://guest:guest@localhost:5672/"
echo "                 Web UI: http://localhost:15672 (guest/guest)"
echo "  PostgreSQL:    postgresql://events_user:password@localhost:5432/events_db"
echo "  MySQL:         mysql://events_user:password@localhost:3306/events_projection"
echo ""
echo "Проверка состояния: docker-compose ps"
echo "Логи:              docker-compose logs -f"
echo "Остановка:         docker-compose down"
echo ""
echo "⚠️  Не забудьте обновить .env файл для использования Docker Compose сервисов!"