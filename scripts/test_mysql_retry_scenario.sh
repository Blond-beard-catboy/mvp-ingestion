#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Тестирование Retry Policy (реальный сценарий) ==="
echo

# 1. Проверяем, что всё запущено
echo "1. Проверка сервисов..."
docker-compose ps | grep -E "(mysql|postgres|rabbitmq|worker)" | grep -q "Up"
if [ $? -ne 0 ]; then
    echo "   ❌ Не все сервисы запущены"
    exit 1
fi
echo "   ✅ Все сервисы запущены"

# 2. Останавливаем MySQL для симуляции сбоя
echo "2. Симуляция transient сбоя MySQL..."
echo "   Останавливаем MySQL..."
docker-compose stop mysql

# 3. Отправляем несколько событий
echo "3. Отправка событий при недоступном MySQL..."
for i in {1..3}; do
    curl -s -X POST http://localhost:5000/events \
      -H "Content-Type: application/json" \
      -d "{
        \"schema_version\": 1,
        \"event_type\": \"retry_test_$i\",
        \"source\": \"retry_test\",
        \"occurred_at\": \"2024-01-15T12:00:00Z\",
        \"payload\": {\"test\": \"mysql_down\", \"iteration\": $i}
      }" > /dev/null
    echo "   Отправлено событие $i"
    sleep 1
done

# 4. Проверяем, что события в PostgreSQL
echo "4. Проверка PostgreSQL..."
PG_COUNT=$(docker-compose exec postgres psql -U events_user -d events_db -t -c "SELECT COUNT(*) FROM events WHERE event_type LIKE 'retry_test_%';" | tr -d ' \n')
echo "   Событий в PostgreSQL: $PG_COUNT (ожидается 3)"

# 5. Запускаем MySQL обратно
echo "5. Восстановление MySQL..."
docker-compose start mysql
echo "   Ждем 10 секунд для восстановления соединения..."
sleep 10

# 6. Отправляем ещё событие
echo "6. Отправка события после восстановления..."
curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "after_recovery_test",
    "source": "retry_test",
    "occurred_at": "2024-01-15T12:05:00Z",
    "payload": {"test": "mysql_recovered"}
  }'
echo "   Событие отправлено"

# 7. Проверяем логи worker на наличие retry
echo "7. Проверка логов worker..."
echo "   Последние 30 строк логов:"
docker-compose logs worker --tail=30 | grep -E "(retry|attempt|mysql.*error|MySQL.*projection)" || echo "   Не найдено записей о retry"

# 8. Итоговая проверка
echo "8. Итоговая проверка состояния..."
sleep 5

echo "   PostgreSQL:"
docker-compose exec postgres psql -U events_user -d events_db -t -c "SELECT event_type, COUNT(*) FROM events WHERE event_type LIKE '%retry%' OR event_type LIKE '%test%' GROUP BY event_type ORDER BY event_type;"

echo "   MySQL:"
docker-compose exec mysql mysql -u events_user -ppassword events_projection -e "SELECT event_type, COUNT(*) FROM events_projection WHERE event_type LIKE '%retry%' OR event_type LIKE '%test%' GROUP BY event_type ORDER BY event_type;" 2>/dev/null || echo "   Ошибка запроса к MySQL"

echo
echo "=== Тест завершен ==="
echo "Ожидаемый результат:"
echo "- PostgreSQL: 4 события (3 при падении MySQL + 1 после восстановления)"
echo "- MySQL: 1 событие (только после восстановления) или 0 (если не успело восстановиться)"
echo "- В логах worker должны быть предупреждения о недоступности MySQL"