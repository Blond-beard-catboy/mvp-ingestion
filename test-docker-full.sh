#!/bin/bash

echo "=== Тест полного Docker пайплайна ==="
echo "Запуск из директории: $(pwd)"
echo ""

# 1. Проверка контейнеров
echo "1. Проверка Docker контейнеров:"
if command -v docker-compose &> /dev/null; then
    docker-compose ps
else
    echo "   docker-compose не найден"
fi

# 2. Проверка API
echo ""
echo "2. Проверка API health:"
API_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5000/health)
HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
API_BODY=$(echo "$API_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ API доступен (код: $HTTP_CODE)"
    echo "$API_BODY" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'   Статус: {data[\"status\"]}')
    print(f'   RabbitMQ: {data[\"rabbitmq\"]}')
except:
    print('   Ошибка парсинга JSON')
"
else
    echo "   ❌ API недоступен (код: $HTTP_CODE)"
fi

# 3. Отправка тестового события
echo ""
echo "3. Отправка тестового события:"
EVENT_DATA='{
    "schema_version": 1,
    "event_type": "final_docker_test",
    "source": "bash_script",
    "occurred_at": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'",
    "payload": {"test": "complete", "docker": true, "timestamp": "'$(date)'"}
}'

RESPONSE=$(curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d "$EVENT_DATA")

if echo "$RESPONSE" | grep -q '"status":"accepted"'; then
    EVENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['event_id'])")
    echo "   ✅ Событие отправлено"
    echo "   Event ID: $EVENT_ID"
    
    # Сохраняем event_id для проверки
    echo "$EVENT_ID" > /tmp/test_event_id.txt
else
    echo "   ❌ Ошибка отправки события"
    echo "   Ответ: $RESPONSE"
    exit 1
fi

# 4. Ожидание обработки
echo ""
echo "4. Ожидание обработки (15 секунд)..."
for i in {1..15}; do
    echo -n "."
    sleep 1
done
echo ""

# 5. Проверка PostgreSQL
echo ""
echo "5. Проверка PostgreSQL:"
if command -v docker-compose &> /dev/null; then
    TOTAL_EVENTS=$(docker-compose exec postgres psql -U events_user -d events_db -t -c "SELECT COUNT(*) FROM events;" 2>/dev/null | tr -d ' \n')
    echo "   Всего событий в БД: $TOTAL_EVENTS"
    
    if [ -f /tmp/test_event_id.txt ]; then
        EVENT_ID=$(cat /tmp/test_event_id.txt)
        echo "   Ищем событие: $EVENT_ID"
        docker-compose exec postgres psql -U events_user -d events_db -c "SELECT event_id, event_type, source, created_at FROM events WHERE event_id = '$EVENT_ID';" 2>/dev/null || echo "   ❌ Событие не найдено"
    fi
else
    echo "   ❌ docker-compose не доступен"
fi

# 6. Проверка RabbitMQ
echo ""
echo "6. Проверка RabbitMQ:"
curl -s -u guest:guest http://localhost:15672/api/queues 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print('   Очереди:')
    for q in data:
        print(f'     - {q[\"name\"]}: {q[\"messages_ready\"]} готово, {q[\"messages\"]} всего')
except Exception as e:
    print(f'   Ошибка: {e}')
"

echo ""
echo "=== Тест завершен ==="
echo "Если видите событие в PostgreSQL и 0 сообщений в очередях - всё работает!"
