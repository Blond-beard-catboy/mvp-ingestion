#!/usr/bin/env python3
"""
Тестирование идемпотентности в PostgreSQL
"""

import sys
import os
from datetime import datetime, timezone
import json

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from shared.db_postgres import PostgresClient


def test_idempotency():
    """Тест идемпотентности: дважды вставляем одно и то же событие"""
    print("=== Тестирование идемпотентности PostgreSQL ===")
    print()
    
    postgres_url = os.getenv('POSTGRES_URL')
    if not postgres_url:
        print("❌ ОШИБКА: POSTGRES_URL не установлен в .env файле")
        print("   Установи в .env: POSTGRES_URL=postgresql://events_user:password@localhost:5432/events_db")
        return False
    
    # Создаём тестовое событие
    test_event_data = {
        "event_id": "test-idempotency-001",
        "schema_version": 1,
        "event_type": "idempotency_test",
        "source": "test_script",
        "occurred_at": datetime.now(timezone.utc).isoformat().replace('+00:00', ''),
        "payload": {
            "test": "idempotency", 
            "timestamp": datetime.now().isoformat(),
            "description": "Тестовое событие для проверки идемпотентности"
        }
    }
    
    print(f"Тестовый event_id: {test_event_data['event_id']}")
    print(f"Тестовое время: {test_event_data['occurred_at']}")
    print()
    
    # Создаём клиент PostgreSQL
    pg_client = PostgresClient(postgres_url)
    
    try:
        # 1. Первая вставка
        print("1. Первая попытка вставки...")
        inserted_first = pg_client.insert_event(test_event_data)
        print(f"   Результат: {'✅ УСПЕШНО' if inserted_first else '❌ НЕ УДАЛОСЬ (уже существует?)'}")
        
        # 2. Вторая вставка (тот же event_id)
        print("2. Вторая попытка вставки (тот же event_id)...")
        inserted_second = pg_client.insert_event(test_event_data)
        print(f"   Результат: {'✅ УСПЕШНО' if inserted_second else '✅ ПРОПУЩЕНО (идемпотентность работает!)'}")
        
        # 3. Проверяем количество записей
        with pg_client.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM events WHERE event_id = %s;", 
                       (test_event_data['event_id'],))
            result = cur.fetchone()
            count = result['count'] if result else 0
        
        print(f"3. Количество записей с event_id '{test_event_data['event_id']}': {count}")
        
        # 4. Получаем событие для проверки
        with pg_client.conn.cursor() as cur:
            cur.execute("SELECT event_id, created_at, occurred_at FROM events WHERE event_id = %s;", 
                       (test_event_data['event_id'],))
            event_in_db = cur.fetchone()
            
        if event_in_db:
            print(f"4. Событие в базе данных: {event_in_db['event_id']}")
            print(f"   Время создания: {event_in_db['created_at']}")
            print(f"   Время события: {event_in_db['occurred_at']}")
        
        print()
        
        # Проверяем результат идемпотентности
        if inserted_first and not inserted_second:
            print("🎉 УСПЕХ: Тест идемпотентности ПРОЙДЕН!")
            print("   - Первая вставка: успешно")
            print("   - Вторая вставка: пропущена (благодаря ON CONFLICT)")
            return True
        else:
            print("❌ НЕУДАЧА: Тест идемпотентности НЕ ПРОЙДЕН!")
            if not inserted_first:
                print("   Причина: Первая вставка не удалась (проверь подключение к PostgreSQL)")
            if inserted_second:
                print("   Причина: Вторая вставка удалась (идемпотентность не работает)")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pg_client.close()


def test_multiple_unique_events():
    """Тест вставки нескольких уникальных событий"""
    print()
    print("=== Тестирование вставки уникальных событий ===")
    
    postgres_url = os.getenv('POSTGRES_URL')
    if not postgres_url:
        print("❌ ОШИБКА: POSTGRES_URL не установлен в .env файле")
        return False
    
    pg_client = PostgresClient(postgres_url)
    
    try:
        # ЯВНО ПОДКЛЮЧАЕМСЯ К БАЗЕ ДАННЫХ
        pg_client.connect()
        
        # Получаем начальное количество событий
        with pg_client.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM events;")
            result = cur.fetchone()
            initial_count = result['count'] if result else 0
        
        print(f"Начальное количество событий: {initial_count}")
        
        # Вставляем 3 уникальных события
        success_count = 0
        for i in range(3):
            event_data = {
                "event_id": f"test-unique-{i}-{datetime.now().timestamp()}",
                "schema_version": 1,
                "event_type": f"test_type_{i}",
                "source": "test_script",
                "occurred_at": datetime.now(timezone.utc).isoformat().replace('+00:00', ''),
                "payload": {
                    "iteration": i,
                    "unique": True,
                    "description": f"Уникальное тестовое событие #{i+1}"
                }
            }
            
            try:
                inserted = pg_client.insert_event(event_data)
                if inserted:
                    success_count += 1
                    print(f"  Событие {i+1}: ✅ УСПЕШНО вставлено")
                else:
                    print(f"  Событие {i+1}: ❌ НЕ УДАЛОСЬ")
            except Exception as e:
                print(f"  Событие {i+1}: ❌ ОШИБКА: {e}")
        
        # Получаем конечное количество событий
        with pg_client.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM events;")
            result = cur.fetchone()
            final_count = result['count'] if result else 0
        
        print(f"Конечное количество событий: {final_count}")
        
        expected_increase = success_count
        actual_increase = final_count - initial_count
        
        if actual_increase == expected_increase:
            print(f"✅ УСПЕХ: Все {success_count} уникальных событий вставлены")
            return True
        else:
            print(f"❌ НЕУДАЧА: Ожидалось +{expected_increase} событий, получено +{actual_increase}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        pg_client.close()


def cleanup_test_data():
    """Очистка тестовых данных"""
    print()
    print("=== Очистка тестовых данных ===")
    
    postgres_url = os.getenv('POSTGRES_URL')
    if not postgres_url:
        print("❌ ОШИБКА: POSTGRES_URL не установлен")
        return
    
    pg_client = PostgresClient(postgres_url)
    
    try:
        pg_client.connect()  # Явно подключаемся
        
        with pg_client.conn.cursor() as cur:
            # Удаляем тестовые записи
            cur.execute("""
                DELETE FROM events 
                WHERE event_id LIKE 'test-%' 
                   OR event_type LIKE 'test_type_%' 
                   OR event_type = 'idempotency_test';
            """)
            deleted_count = cur.rowcount
            pg_client.conn.commit()
        
        print(f"Удалено тестовых записей: {deleted_count}")
        
    except Exception as e:
        print(f"Ошибка при очистке: {e}")
    finally:
        pg_client.close()


if __name__ == '__main__':
    print("Тестирование идемпотентности PostgreSQL")
    print("=" * 50)
    
    # Тестируем идемпотентность
    success1 = test_idempotency()
    
    if success1:
        # Тестируем вставку уникальных событий
        success2 = test_multiple_unique_events()
    else:
        success2 = False
    
    # Очищаем тестовые данные
    cleanup_test_data()
    
    print()
    print("=" * 50)
    
    if success1 and success2:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        sys.exit(0)
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        sys.exit(1)