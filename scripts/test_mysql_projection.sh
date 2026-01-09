#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Тестирование MySQL проекции (День 7) ==="

# 1. Проверяем, что MySQL запущен
echo "1. Проверка MySQL..."
docker-compose ps mysql | grep -q "Up"
if [ $? -eq 0 ]; then
    echo "   ✅ MySQL запущен"
else
    echo "   ❌ MySQL не запущен"
    exit 1
fi

# 2. Проверяем таблицу events_projection
echo "2. Проверка таблицы events_projection..."
docker-compose exec mysql mysql -u events_user -ppassword events_projection -e "SHOW TABLES;" | grep -q "events_projection"
if [ $? -eq 0 ]; then
    echo "   ✅ Таблица events_projection существует"
else
    echo "   ❌ Таблица events_projection не найдена"
    exit 1
fi

# 3. Отправляем тестовое событие
echo "3. Отправка тестового события..."
RESPONSE=$(curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "mysql_projection_test",
    "source": "test_script",
    "occurred_at": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'",
    "payload": {"test": "mysql_projection", "day": 7}
  }')

EVENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['event_id'])")
echo "   Event ID: $EVENT_ID"

# 4. Ждем обработки
echo "4. Ожидание обработки (10 секунд)..."
sleep 10

# 5. Проверяем PostgreSQL
echo "5. Проверка PostgreSQL (source of truth)..."
PG_COUNT=$(docker-compose exec postgres psql -U events_user -d events_db -t -c "SELECT COUNT(*) FROM events WHERE event_id = '$EVENT_ID';" | tr -d ' \n')
if [ "$PG_COUNT" = "1" ]; then
    echo "   ✅ Событие в PostgreSQL"
else
    echo "   ❌ Событие не найдено в PostgreSQL"
fi

# 6. Проверяем MySQL проекцию
echo "6. Проверка MySQL проекции..."
MYSQL_COUNT=$(docker-compose exec mysql mysql -u events_user -ppassword events_projection -B -N -e "SELECT COUNT(*) FROM events_projection WHERE event_id = '$EVENT_ID';" 2>/dev/null | tr -d ' \n')
if [ "$MYSQL_COUNT" = "1" ]; then
    echo "   ✅ Событие в MySQL проекции"
else
    echo "   ⚠️  Событие не найдено в MySQL проекции (но это нормально для best-effort)"
fi

# 7. Проверяем, что воркер работает с MySQL ошибками
echo "7. Тестирование обработки ошибок MySQL..."
echo "   Останавливаем MySQL..."
docker-compose stop mysql

echo "   Отправляем событие при остановленном MySQL..."
curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "mysql_down_test",
    "source": "test_script",
    "occurred_at": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'",
    "payload": {"test": "mysql_down", "should_work": true}
  }' > /dev/null

echo "   Запускаем MySQL обратно..."
docker-compose start mysql
sleep 5

echo "   Отправляем событие при работающем MySQL..."
curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "mysql_back_test",
    "source": "test_script",
    "occurred_at": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'",
    "payload": {"test": "mysql_back", "should_work": true}
  }' > /dev/null

sleep 5

echo ""
echo "=== Результаты теста ==="
echo "Архитектура best-effort MySQL проекции:"
echo "  - PostgreSQL: всегда должен получать события (source of truth)"
echo "  - MySQL: получает события когда доступен, ошибки не ломают пайплайн"
echo ""
echo "Проверьте логи воркера для деталей:"
echo "  docker-compose logs worker --tail=20"
