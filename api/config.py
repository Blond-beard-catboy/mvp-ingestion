import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'
    
    # Ограничения
    MAX_BODY_BYTES = int(os.getenv('MAX_BODY_BYTES', 1000000))
    
    # RabbitMQ
    RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
    RABBIT_QUEUE_EVENTS = os.getenv('RABBIT_QUEUE_EVENTS', 'events')
    RABBIT_QUEUE_DLQ = os.getenv('RABBIT_QUEUE_DLQ', 'events.dlq')
    
    # Базы данных (для будущего использования)
    POSTGRES_URL = os.getenv('POSTGRES_URL')
    MYSQL_URL = os.getenv('MYSQL_URL')
    
    # Логирование
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')