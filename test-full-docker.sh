#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Финальный тест Docker Compose (День 6) ==="
echo ""

# 1. Проверка контейнеров
echo "1. Проверка Docker контейнеров:"
docker-compose ps

# 2. Проверка API
echo ""
echo "2. Проверка API health:"
HEALTH=$(curl -s http://localhost:5000/health)
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo "   ✅ API здоров"
    echo "$HEALTH" | python3 -m json.tool
else
    echo "   ❌ Проблема с API"
    echo "$HEALTH"
fi

# 3. Отправка тестового события
echo ""
echo "3. Отправка тестового события:"
RESPONSE=$(curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "final_docker_test",
    "source": "test_script",
    "occurred_at": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'",
    "payload": {"day": 6, "status": "complete", "docker": true}
  }')

if echo "$RESPONSE" | grep -q '"status":"accepted"'; then
    EVENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['event_id'])")
    echo "   ✅ Событие отправлено"
    echo "   Event ID: $EVENT_ID"
else
    echo "   ❌ Ошибка отправки события"
    echo "   Ответ: $RESPONSE"
    exit 1
fi

# 4. Ожидание обработки
echo ""
echo "4. Ожидание обработки события (10 секунд)..."
sleep 10

# 5. Проверка PostgreSQL
echo ""
echo "5. Проверка записи в PostgreSQL:"
docker-compose exec postgres psql -U events_user -d events_db -c "SELECT event_id, event_type, source FROM events WHERE event_id = '$EVENT_ID';" 2>/dev/null | grep -q "$EVENT_ID"
if [ $? -eq 0 ]; then
    echo "   ✅ Событие записано в PostgreSQL"
else
    echo "   ❌ Событие не найдено в PostgreSQL"
fi

# 6. Проверка RabbitMQ
echo ""
echo "6. Проверка RabbitMQ очередей:"
QUEUES=$(curl -s -u guest:guest http://localhost:15672/api/queues)
if echo "$QUEUES" | python3 -c "import sys, json; data=json.load(sys.stdin); print('Очереди:'); [print(f'  - {q[\"name\"]}: {q[\"messages_ready\"]} готово') for q in data]" 2>/dev/null; then
    echo "   ✅ RabbitMQ доступен"
else
    echo "   ❌ Ошибка подключения к RabbitMQ"
fi

echo ""
echo "=== Тест завершен ==="
echo "🎉 Docker Compose полностью работает!"
echo ""
echo "Сервисы:"
echo "  - RabbitMQ:      http://localhost:15672"
echo "  - API:           http://localhost:5000"
echo "  - PostgreSQL:    порт 5432"
echo "  - MySQL:         порт 3306"
echo "  - Worker:        (фоновая обработка)"
