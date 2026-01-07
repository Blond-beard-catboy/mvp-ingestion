#!/bin/bash

echo "=== Инициализация RabbitMQ очередей ==="

# Проверяем доступность RabbitMQ
if ! curl -s http://localhost:15672 > /dev/null 2>&1; then
    echo "❌ RabbitMQ недоступен на localhost:15672"
    exit 1
fi

echo "RabbitMQ доступен"

# Создаем основную очередь events
echo "Создаем очередь 'events'..."
curl -u guest:guest -H "content-type:application/json" -X PUT \
  http://localhost:15672/api/queues/%2F/events \
  -d '{
    "auto_delete": false,
    "durable": true,
    "arguments": {
      "x-dead-letter-exchange": "",
      "x-dead-letter-routing-key": "events.dlq"
    }
  }'

echo ""
echo "Создаем очередь 'events.dlq'..."
curl -u guest:guest -H "content-type:application/json" -X PUT \
  http://localhost:15672/api/queues/%2F/events.dlq \
  -d '{
    "auto_delete": false,
    "durable": true
  }'

echo ""
echo "Проверяем созданные очереди:"
curl -s -u guest:guest http://localhost:15672/api/queues | python3 -c "
import json, sys
try:
    queues = json.load(sys.stdin)
    if queues:
        print('✅ Созданы очереди:')
        for q in queues:
            print(f'   - {q[\"name\"]} (сообщений: {q[\"messages\"]})')
    else:
        print('❌ Очереди не созданы')
except Exception as e:
    print(f'Ошибка: {e}')
"
