#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Проверка Docker Compose сервисов ==="
echo ""

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Ошибка: docker-compose не найден"
    exit 1
fi

echo "1. Состояние контейнеров:"
docker-compose ps

echo ""
echo "2. Проверка RabbitMQ:"
if curl -s http://localhost:15672 > /dev/null 2>&1; then
    echo "   ✅ RabbitMQ доступен"
else
    echo "   ❌ RabbitMQ недоступен"
fi

echo ""
echo "3. Проверка PostgreSQL:"
if command -v psql &> /dev/null; then
    if PGPASSWORD=password psql -h localhost -p 5432 -U events_user -d events_db -c "SELECT 1" > /dev/null 2>&1; then
        echo "   ✅ PostgreSQL доступен"
        echo "   📊 Таблицы в БД:"
        PGPASSWORD=password psql -h localhost -p 5432 -U events_user -d events_db -c "\dt" 2>/dev/null || echo "   Не удалось получить список таблиц"
    else
        echo "   ❌ PostgreSQL недоступен"
    fi
else
    echo "   ⚠️  psql не установлен, проверка PostgreSQL пропущена"
fi

echo ""
echo "4. Проверка MySQL:"
if command -v mysql &> /dev/null; then
    if mysql -h localhost -P 3306 -u events_user -ppassword events_projection -e "SELECT 1" > /dev/null 2>&1; then
        echo "   ✅ MySQL доступен"
        echo "   📊 Таблицы в БД:"
        mysql -h localhost -P 3306 -u events_user -ppassword events_projection -e "SHOW TABLES" 2>/dev/null || echo "   Не удалось получить список таблиц"
    else
        echo "   ❌ MySQL недоступен"
    fi
else
    echo "   ⚠️  mysql клиент не установлен, проверка MySQL пропущена"
fi

echo ""
echo "=== Проверка завершена ==="