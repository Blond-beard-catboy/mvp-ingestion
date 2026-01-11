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


def send_malformed_json():
    """Отправка битого JSON"""
    producer = RabbitMQProducer(Config.RABBIT_URL)
    
    # Битый JSON
    bad_json = b'{"event_id": "test-bad-json", "event_type": "test", "occurred_at": "2024-01-15T10:30:00Z", invalid json'
    
    producer.publish(
        queue_name=Config.RABBIT_QUEUE_EVENTS,
        message_body=bad_json
    )
    print("Sent malformed JSON to queue")


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
    send_malformed_json()
    
    print("\n" + "=" * 50)
    print("Done! Check RabbitMQ management console:")
    print(f"  URL: http://localhost:15672 (if management plugin enabled)")
    print(f"  Queue: {Config.RABBIT_QUEUE_EVENTS}")