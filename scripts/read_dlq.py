#!/usr/bin/env python3
"""
Скрипт для чтения и анализа сообщений из DLQ
"""
import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.rabbit import RabbitMQConsumer
from worker.config import Config


def read_dlq(limit: int = 10, save_to_file: bool = False):
    """Чтение сообщений из DLQ"""
    print(f"=== Reading DLQ (limit: {limit}) ===")
    
    consumer = RabbitMQConsumer(Config.RABBIT_URL)
    consumer.connect()
    
    messages = []
    
    def callback(ch, method, properties, body):
        try:
            decoded_body = body.decode('utf-8', errors='replace')
            
            # Пытаемся разобрать как JSON
            try:
                message = json.loads(decoded_body)
            except json.JSONDecodeError:
                # Если не JSON, показываем сырое сообщение
                message = {
                    "raw_message": decoded_body,
                    "error": "Invalid JSON format in DLQ message",
                    "is_raw": True
                }
            
            messages.append({
                "delivery_tag": method.delivery_tag,
                "message": message,
                "properties": {
                    "headers": properties.headers if properties.headers else None
                }
            })
            
            # Подтверждаем прочтение
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            if len(messages) >= limit:
                ch.stop_consuming()
                
        except Exception as e:
            print(f"Error processing DLQ message: {e}")
            print(f"Raw body (first 200 chars): {body[:200] if body else 'empty'}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    # Начинаем потребление
    if consumer.channel:
        consumer.channel.basic_qos(prefetch_count=1)
        consumer.channel.basic_consume(
            queue=Config.RABBIT_QUEUE_DLQ,
            on_message_callback=callback,
            auto_ack=False
        )
        
        print(f"Waiting for messages in DLQ '{Config.RABBIT_QUEUE_DLQ}'...")
        consumer.channel.start_consuming()
    
    # Вывод результатов
    print(f"\nFound {len(messages)} messages in DLQ:")
    print("=" * 80)
    
    for i, msg in enumerate(messages, 1):
        print(f"\n{i}. Delivery tag: {msg['delivery_tag']}")
        
        # Заголовки
        headers = msg['properties']['headers']
        if headers:
            print(f"   Error reason: {headers.get('x-death-reason', 'unknown')}")
            print(f"   Original queue: {headers.get('x-original-queue', 'unknown')}")
        else:
            print(f"   Error reason: unknown (no headers)")
            print(f"   Original queue: unknown")
        
        # Сообщение
        message = msg['message']
        
        if message.get('is_raw'):
            # Сырое сообщение (не JSON)
            print(f"   Message type: RAW (not JSON)")
            print(f"   Raw content: {message.get('raw_message', '')[:200]}...")
        elif 'timestamp' in message:
            # Наше обогащенное сообщение
            print(f"   Timestamp: {message.get('timestamp')}")
            print(f"   Original queue: {message.get('queue', 'unknown')}")
            
            error_info = message.get('error_info', {})
            print(f"   Error reason: {error_info.get('reason', 'unknown')}")
            print(f"   Exception type: {error_info.get('exception_type', 'unknown')}")
            print(f"   Error details: {error_info.get('error', 'No details')[:200]}...")
            
            original_msg = message.get('original_message', '')
            if len(original_msg) > 200:
                print(f"   Original message: {original_msg[:200]}...")
            else:
                print(f"   Original message: {original_msg}")
        else:
            # Неизвестный формат
            print(f"   Message type: UNKNOWN FORMAT")
            print(f"   Content: {str(message)[:200]}...")
        
        print("-" * 80)
    
    # Сохранение в файл
    if save_to_file and messages:
        filename = f"dlq_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(messages, f, indent=2, default=str)
        print(f"\nMessages saved to: {filename}")
    
    consumer.close()


def purge_dlq():
    """Очистка DLQ (подтверждение всех сообщений)"""
    print("=== Purging DLQ ===")
    
    consumer = RabbitMQConsumer(Config.RABBIT_URL)
    consumer.connect()
    
    if consumer.channel:
        # Получаем количество сообщений
        queue_info = consumer.channel.queue_declare(
            queue=Config.RABBIT_QUEUE_DLQ,
            passive=True
        )
        message_count = queue_info.method.message_count
        
        print(f"Messages in DLQ before purge: {message_count}")
        
        if message_count > 0:
            # Подтверждаем все сообщения
            for _ in range(message_count):
                method_frame, _, body = consumer.channel.basic_get(
                    queue=Config.RABBIT_QUEUE_DLQ,
                    auto_ack=True
                )
                if method_frame:
                    print(f"  Purged message: {method_frame.delivery_tag}")
        
        # Получаем новое количество
        queue_info = consumer.channel.queue_declare(
            queue=Config.RABBIT_QUEUE_DLQ,
            passive=True
        )
        print(f"Messages in DLQ after purge: {queue_info.method.message_count}")
    
    consumer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DLQ Reader Tool')
    parser.add_argument('--limit', type=int, default=10, help='Max messages to read')
    parser.add_argument('--save', action='store_true', help='Save messages to file')
    parser.add_argument('--purge', action='store_true', help='Purge all messages from DLQ')
    
    args = parser.parse_args()
    
    if args.purge:
        purge_dlq()
    else:
        read_dlq(limit=args.limit, save_to_file=args.save)