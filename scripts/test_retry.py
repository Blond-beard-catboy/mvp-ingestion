#!/usr/bin/env python3
"""
Тестирование retry policy для MySQL
"""
import sys
import os
import time
from datetime import datetime, timezone
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from shared.db_mysql import MySQLClient
from shared.utils import retry, RetryConfig, is_retryable_error


def test_retry_decorator():
    """Тест retry декоратора"""
    print("=== Тестирование Retry Decorator ===")
    print()
    
    attempt_count = 0
    
    @retry(max_attempts=3, delay=0.1, backoff=2.0)
    def function_with_transient_error():
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 3:
            raise ConnectionError(f"Simulated transient error (attempt {attempt_count})")
        return f"✅ Success on attempt {attempt_count}"
    
    try:
        result = function_with_transient_error()
        print(f"1. Retry decorator test: {result}")
        print(f"   Total attempts: {attempt_count}")
        print()
        return True
    except Exception as e:
        print(f"❌ Retry decorator failed: {e}")
        print()
        return False


def test_is_retryable_error():
    """Тест классификации ошибок"""
    print("2. Testing error classification:")
    
    test_errors = [
        (ConnectionError("Connection refused"), True),
        (TimeoutError("Operation timed out"), True),
        (ValueError("Invalid value"), False),
        (Exception("MySQL server has gone away"), True),
        (Exception("Deadlock found when trying to get lock"), True),
        (Exception("Duplicate entry '123' for key 'PRIMARY'"), False),
    ]
    
    all_passed = True
    for error, expected_retryable in test_errors:
        is_retry = is_retryable_error(error)
        passed = is_retry == expected_retryable
        status = "✅" if passed else "❌"
        
        print(f"   {status} {type(error).__name__}: '{error}'")
        print(f"     Expected: {'RETRYABLE' if expected_retryable else 'NON-RETRYABLE'}")
        print(f"     Got: {'RETRYABLE' if is_retry else 'NON-RETRYABLE'}")
        
        if not passed:
            all_passed = False
    
    print()
    return all_passed


def test_mysql_retry_integration():
    """Интеграционный тест с реальным MySQL"""
    print("3. Testing MySQL retry integration:")
    
    mysql_url = os.getenv('MYSQL_URL')
    if not mysql_url:
        print("   ⚠️  MYSQL_URL не установлен, пропускаем интеграционный тест")
        print()
        return None
    
    client = MySQLClient(mysql_url)
    
    try:
        # Тест нормальной вставки
        event_data = {
            "event_id": f"retry-test-{int(time.time())}",
            "event_type": "retry_test",
            "source": "test_script",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": {"test": "retry_integration"}
        }
        
        # Используем метод с retry
        success = client.upsert_projection_with_retry(event_data)
        
        if success:
            print("   ✅ MySQL retry integration test passed")
            print(f"   Event ID: {event_data['event_id']}")
        else:
            print("   ⚠️  MySQL projection failed (non-retryable error)")
        
        print()
        return success
        
    except Exception as e:
        print(f"   ❌ MySQL retry integration test failed: {e}")
        print()
        return False
    finally:
        try:
            client.close()
        except AttributeError as e:
            # Игнорируем ошибку close, если метод не существует
            print(f"   ⚠️  Warning during MySQL client close: {e}")


def simulate_transient_failure():
    """Симуляция transient сбоя"""
    print("4. Simulating transient failure scenario:")
    
    class TransientError(Exception):
        pass
    
    call_count = 0
    
    def unreliable_operation():
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            raise TransientError("First attempt failed")
        elif call_count == 2:
            raise ConnectionError("Second attempt failed")
        else:
            return f"Success on attempt {call_count}"
    
    # Обернем в retry
    retryable_op = retry(max_attempts=3, delay=0.1, backoff=1.5)(unreliable_operation)
    
    try:
        result = retryable_op()
        print(f"   ✅ {result}")
        print(f"   Total calls: {call_count}")
        print()
        return True
    except Exception as e:
        print(f"   ❌ Failed after retries: {e}")
        print()
        return False


def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("Тестирование Retry Policy (Day 8)")
    print("=" * 60)
    print()
    
    results = []
    
    # Запуск тестов
    results.append(("Retry Decorator", test_retry_decorator()))
    results.append(("Error Classification", test_is_retryable_error()))
    
    mysql_test_result = test_mysql_retry_integration()
    if mysql_test_result is not None:
        results.append(("MySQL Integration", mysql_test_result))
    
    results.append(("Transient Failure Simulation", simulate_transient_failure()))
    
    # Вывод итогов
    print("=" * 60)
    print("Итоги тестирования:")
    print()
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ ПРОЙДЕН" if passed else "❌ НЕ ПРОЙДЕН"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    print("=" * 60)
    
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return 1


if __name__ == '__main__':
    sys.exit(main())