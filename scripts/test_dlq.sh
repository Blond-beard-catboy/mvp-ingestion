#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Тестирование DLQ (День 9) ==="

# 1. Проверяем, что DLQ существует
echo "1. Проверка DLQ очереди..."
docker-compose exec rabbitmq rabbitmqctl list_queues name messages | grep "events.dlq"
if [ $? -eq 0 ]; then
    echo "   ✅ DLQ очередь существует"
else
    echo "   ❌ DLQ очередь не найдена"
    exit 1
fi

# 2. Отправляем валидное сообщение
echo "2. Отправка валидного сообщения..."
curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "dlq_test_valid",
    "source": "test_script",
    "occurred_at": "2024-01-15T12:00:00Z",
    "payload": {"test": "valid_message"}
  }'

# 3. Отправляем невалидный JSON
echo "3. Отправка невалидного JSON..."
python -c "
import sys
sys.path.append('.')
from shared.rabbit import RabbitMQProducer
from api.config import Config

producer = RabbitMQProducer(Config.RABBIT_URL)
producer.publish(
    queue_name='events',
    message_body=b'{\"event_id\": \"test-bad-json\", invalid json here'
)
print('   Sent malformed JSON')
"

# 4. Отправляем сообщение с ошибкой валидации
echo "4. Отправка сообщения с ошибкой валидации..."
curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 0,
    "event_type": "",
    "source": "test",
    "occurred_at": "invalid_date",
    "payload": {}
  }'

# 5. Ждем обработки
echo "5. Ожидание обработки (10 секунд)..."
sleep 10

# 6. Проверяем DLQ
echo "6. Проверка DLQ..."
docker-compose exec rabbitmq rabbitmqctl list_queues name messages | grep "events.dlq"

# 7. Читаем DLQ
echo "7. Чтение сообщений из DLQ..."
python scripts/read_dlq.py --limit 5

echo ""
echo "=== Ожидаемый результат ==="
echo "- Валидное сообщение: должно обработаться без ошибок"
echo "- Невалидный JSON: должен попасть в DLQ"
echo "- Сообщение с ошибкой валидации: должно попасть в DLQ"
echo "- В логах worker должны быть ошибки и информация об отправке в DLQ"