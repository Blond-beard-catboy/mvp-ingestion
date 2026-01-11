import pika
import json
import logging
from typing import Optional, Callable
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import BasicProperties
from datetime import datetime

logger = logging.getLogger(__name__)


def get_connection(url: str) -> pika.BlockingConnection:
    """
    Создание подключения к RabbitMQ
    
    Args:
        url: URL подключения (amqp://user:pass@host:port/)
    
    Returns:
        Подключение к RabbitMQ
    """
    try:
        connection = pika.BlockingConnection(pika.URLParameters(url))
        logger.info(f"Connected to RabbitMQ at {url}")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise


class RabbitMQProducer:
    """Продюсер для отправки сообщений в RabbitMQ"""
    
    def __init__(self, rabbit_url: str):
        """
        Инициализация продюсера
        
        Args:
            rabbit_url: URL подключения к RabbitMQ
        """
        self.rabbit_url = rabbit_url
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
    
    def connect(self) -> None:
        """Установка соединения с RabbitMQ"""
        if self.connection is None or self.connection.is_closed:
            self.connection = get_connection(self.rabbit_url)
            self.channel = self.connection.channel()
            
            # Настраиваем обменник и очереди
            self.setup_infrastructure()
    
    def setup_infrastructure(self) -> None:
        """Настройка очередей и обменников"""
        if self.channel is None:
            raise RuntimeError("Channel not initialized")
        
        # Объявляем основную очередь с DLQ
        self.channel.queue_declare(
            queue='events',
            durable=True,  # Сохранять сообщения при перезагрузке RabbitMQ
            arguments={
                'x-dead-letter-exchange': '',  # Используем default exchange для DLQ
                'x-dead-letter-routing-key': 'events.dlq'
            }
        )
        
        # Объявляем DLQ очередь
        self.channel.queue_declare(
            queue='events.dlq',
            durable=True
        )
        
        logger.info("RabbitMQ infrastructure setup complete")
    
    def publish(self, 
                queue_name: str, 
                message_body: bytes, 
                headers: Optional[dict] = None) -> None:
        """
        Публикация сообщения в очередь
        
        Args:
            queue_name: Имя очереди
            message_body: Тело сообщения в bytes
            headers: Дополнительные заголовки сообщения
        """
        self.connect()
        
        if self.channel is None:
            raise RuntimeError("Channel not initialized")
        
        # Свойства сообщения
        properties = BasicProperties(
            delivery_mode=2,  # Persistent (сохранять на диске)
            content_type='application/json',
            headers=headers or {}
        )
        
        try:
            self.channel.basic_publish(
                exchange='',  # Используем default exchange
                routing_key=queue_name,
                body=message_body,
                properties=properties,
                mandatory=True  # Гарантировать доставку
            )
            logger.info(f"Message published to queue '{queue_name}'")
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {e}")
            raise
    
    def close(self) -> None:
        """Закрытие соединения с RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def publish_to_dlq(rabbit_url: str, original_message: bytes, error_info: dict, queue_name: str = "events.dlq"):
    """Публикация сообщения в Dead Letter Queue
    Args:
    rabbit_url: URL RabbitMQ
    original_message: Оригинальное сообщение (bytes)
    error_info: Информация об ошибке (dict)
    queue_name: Имя DLQ (по умолчанию 'events.dlq')
    """
    # Формируем обогащенное сообщение для DLQ
    dlq_message = {
        "original_message": original_message.decode('utf-8', errors='replace'),
        "error_info": error_info,
        "timestamp": datetime.utcnow().isoformat(),
        "queue": "events"
    }
        
    # Публикуем в DLQ
    producer = RabbitMQProducer(rabbit_url)
    producer.publish(
        queue_name=queue_name,
        message_body=json.dumps(dlq_message).encode('utf-8'),
        headers={
            "x-death-reason": error_info.get("reason", "unknown"),
            "x-original-queue": "events"
        }
    )
    producer.close()

class RabbitMQConsumer:
    """Консьюмер для чтения сообщений из RabbitMQ"""
    
    def __init__(self, rabbit_url: str):
        self.rabbit_url = rabbit_url
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
    
    def connect(self) -> None:
        """Установка соединения с RabbitMQ"""
        if self.connection is None or self.connection.is_closed:
            self.connection = get_connection(self.rabbit_url)
            self.channel = self.connection.channel()
            
            # Объявляем очередь, если не объявлена
            self.channel.queue_declare(
                queue='events',
                durable=True,
                arguments={
                    'x-dead-letter-exchange': '',
                    'x-dead-letter-routing-key': 'events.dlq'
                }
            )
            
            # Объявляем DLQ
            self.channel.queue_declare(
                queue='events.dlq',
                durable=True
            )
            
            logger.info("RabbitMQ consumer connected and queues declared")
    
    def consume(self, queue_name: str, callback: Callable) -> None:
        """
        Начать потребление сообщений из очереди
        
        Args:
            queue_name: Имя очереди
            callback: Функция для обработки сообщений
        """
        self.connect()
        
        if self.channel is None:
            raise RuntimeError("Channel not initialized")
        
        # Ограничиваем количество неподтверждённых сообщений
        self.channel.basic_qos(prefetch_count=1)
        
        # Начинаем потребление
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False  # Ручное подтверждение!
        )
        
        logger.info(f"Started consuming from queue '{queue_name}'")
    
    def start_consuming(self) -> None:
        """Запуск бесконечного цикла потребления"""
        if self.channel is None:
            raise RuntimeError("Channel not initialized")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consuming stopped by user")
        except Exception as e:
            logger.error(f"Error in consuming loop: {e}")
            raise
    
    def ack(self, delivery_tag: int) -> None:
        """Подтверждение успешной обработки сообщения"""
        if self.channel is None:
            raise RuntimeError("Channel not initialized")
        
        self.channel.basic_ack(delivery_tag=delivery_tag)
        logger.debug(f"Message acknowledged: {delivery_tag}")
    
    def nack(self, delivery_tag: int, requeue: bool = False) -> None:
        """Отрицательное подтверждение (сообщение не обработано)"""
        if self.channel is None:
            raise RuntimeError("Channel not initialized")
        
        self.channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
        logger.warning(f"Message rejected: {delivery_tag}, requeue={requeue}")
    
    def close(self) -> None:
        """Закрытие соединения с RabbitMQ"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ consumer connection closed")
