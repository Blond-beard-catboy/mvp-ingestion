#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from shared.db_postgres import PostgresClient

print("=== Тест подключения к PostgreSQL ===")

postgres_url = os.getenv('POSTGRES_URL')
if not postgres_url:
    print("❌ ОШИБКА: POSTGRES_URL не найден в .env")
    sys.exit(1)

print(f"URL: {postgres_url}")

try:
    client = PostgresClient(postgres_url)
    client.connect()
    
    # Проверяем существование таблицы
    with client.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM events;")
        result = cur.fetchone()
        print(f"✅ Подключение успешно. Таблица events существует.")
        print(f"   Количество записей: {result['count']}")
    
    client.close()
    
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    sys.exit(1)

print("✅ Тест завершён успешно!")
