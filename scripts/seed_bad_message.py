#!/usr/bin/env python3
"""
Скрипт для отправки тестовых "плохих" сообщений в RabbitMQ
"""
import sys
import os
import json
import time

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.rabbit import RabbitMQProducer
from api.config import Config


def send_bad_message():
    """Отправляет тестовое плохое сообщение"""
    producer = RabbitMQProducer(Config.RABBIT_URL)
    
    # Пример "плохого" сообщения (невалидный JSON, но в байтах)
    bad_message = {
        "event_id": "test-bad-message-001",
        "schema_version": 1,
        "event_type": "malformed_event",
        "source": "test_script",
        "occurred_at": "2024-01-15T10:30:00Z",
        "payload": {
            "malformed": True,
            "invalid_field": b"binary data that might break things",  # Несериализуемо в JSON
            "nested": {
                "deeply": {
                    "recursive": "..." * 10000  # Очень большая строка
                }
            }
        }
    }
    
    # Намеренно портим JSON
    message_body = json.dumps(bad_message).encode('utf-8')
    # Добавляем лишние байты в конец
    message_body += b"invalid bytes at the end"
    
    try:
        producer.publish(
            queue_name=Config.RABBIT_QUEUE_EVENTS,
            message_body=message_body
        )
        print(f"✓ Sent bad message to queue '{Config.RABBIT_QUEUE_EVENTS}'")
        print(f"  Message ID: {bad_message['event_id']}")
        print(f"  Note: This message will likely fail during processing")
        
    except Exception as e:
        print(f"✗ Failed to send message: {e}")
        sys.exit(1)


def send_valid_message_for_test():
    """Отправляет валидное тестовое сообщение"""
    producer = RabbitMQProducer(Config.RABBIT_URL)
    
    valid_message = {
        "event_id": f"test-valid-{int(time.time())}",
        "schema_version": 1,
        "event_type": "test_event",
        "source": "seed_script",
        "occurred_at": "2024-01-15T10:30:00Z",
        "payload": {
            "test": True,
            "timestamp": time.time(),
            "description": "Valid test message from seed script"
        }
    }
    
    message_body = json.dumps(valid_message).encode('utf-8')
    
    try:
        producer.publish(
            queue_name=Config.RABBIT_QUEUE_EVENTS,
            message_body=message_body
        )
        print(f"\n✓ Sent valid test message")
        print(f"  Event ID: {valid_message['event_id']}")
        
    except Exception as e:
        print(f"✗ Failed to send valid message: {e}")


if __name__ == '__main__':
    print("RabbitMQ Seed Message Script")
    print("=" * 50)
    
    # Отправляем оба типа сообщений
    send_valid_message_for_test()
    send_bad_message()
    
    print("\n" + "=" * 50)
    print("Done! Check RabbitMQ management console:")
    print(f"  URL: http://localhost:15672 (if management plugin enabled)")
    print(f"  Queue: {Config.RABBIT_QUEUE_EVENTS}")