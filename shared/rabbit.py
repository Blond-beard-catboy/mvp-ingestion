import pika
import json
import logging
from typing import Optional
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import BasicProperties

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