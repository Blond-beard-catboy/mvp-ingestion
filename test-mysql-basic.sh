#!/bin/bash
cd ~/mvp_ingestion

echo "=== Базовый тест MySQL проекции ==="
echo ""

# 1. Проверяем подключение к MySQL
echo "1. Проверка подключения к MySQL из воркера..."
docker-compose exec worker python3 -c "
import os, sys
sys.path.append('/app')
from shared.db_mysql import MySQLClient

try:
    mysql_url = os.getenv('MYSQL_URL', 'mysql://events_user:password@mysql:3306/events_projection')
    print(f'   MySQL URL: {mysql_url}')
    
    client = MySQLClient(mysql_url)
    client.connect()
    print('   ✅ Подключение к MySQL успешно')
    
    # Проверяем таблицу
    conn = client.get_connection()
    cursor = conn.cursor()
    cursor.execute('SHOW TABLES LIKE \"events_projection\"')
    result = cursor.fetchone()
    if result:
        print('   ✅ Таблица events_projection существует')
    else:
        print('   ❌ Таблица events_projection не найдена')
    cursor.close()
    
except Exception as e:
    print(f'   ❌ Ошибка подключения к MySQL: {e}')
"

# 2. Отправляем тестовое событие
echo ""
echo "2. Отправка тестового события..."
RESPONSE=$(curl -s -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "mysql_projection_test",
    "source": "test_script",
    "occurred_at": "'$(date -u +"%Y-%m-%dT%H:%M:%S")'",
    "payload": {"test": "mysql_projection", "day": 7}
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

# 3. Ждем обработки
echo ""
echo "3. Ожидание обработки (10 секунд)..."
sleep 10

# 4. Проверяем PostgreSQL (source of truth)
echo ""
echo "4. Проверка PostgreSQL (source of truth):"
PG_RESULT=$(docker-compose exec postgres psql -U events_user -d events_db -t -c "SELECT event_id, event_type FROM events WHERE event_id = '$EVENT_ID';" 2>/dev/null)
if echo "$PG_RESULT" | grep -q "$EVENT_ID"; then
    echo "   ✅ Событие записано в PostgreSQL"
else
    echo "   ❌ Событие не найдено в PostgreSQL"
    exit 1
fi

# 5. Проверяем MySQL проекцию
echo ""
echo "5. Проверка MySQL проекции:"
MYSQL_RESULT=$(docker-compose exec mysql mysql -u events_user -ppassword events_projection -B -N -e "SELECT event_id, event_type FROM events_projection WHERE event_id = '$EVENT_ID';" 2>/dev/null)
if echo "$MYSQL_RESULT" | grep -q "$EVENT_ID"; then
    echo "   ✅ Событие записано в MySQL проекцию"
else
    echo "   ❌ Событие не найдено в MySQL проекции"
    echo "   Возможные причины:"
    echo "   - Ошибка в shared/db_mysql.py"
    echo "   - Неправильный MYSQL_URL в .env"
    echo "   - Таблица events_projection не создана"
fi

# 6. Проверяем лог воркера (ИСПРАВЛЕННАЯ КОМАНДА)
echo ""
echo "6. Последние логи воркера:"
docker-compose logs --tail 10 worker 2>&1 | grep -E "(Processing|MySQL|PostgreSQL|ERROR|Error|error)" | tail -10

echo ""
echo "=== Базовый тест завершен ==="
