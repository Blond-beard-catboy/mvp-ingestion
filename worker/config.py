import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Config:
    """Конфигурация воркера"""
    
    # RabbitMQ
    RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
    RABBIT_QUEUE_EVENTS = os.getenv('RABBIT_QUEUE_EVENTS', 'events')
    RABBIT_QUEUE_DLQ = os.getenv('RABBIT_QUEUE_DLQ', 'events.dlq')
    
    # PostgreSQL
    POSTGRES_URL = os.getenv('POSTGRES_URL')
    
    # Настройки воркера
    WORKER_PREFETCH_COUNT = int(os.getenv('WORKER_PREFETCH_COUNT', 1))  # По 1 сообщению за раз
    WORKER_RECONNECT_DELAY = int(os.getenv('WORKER_RECONNECT_DELAY', 5))  # Задержка переподключения
    
    # Логирование
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Обработка ошибок
    MAX_PROCESSING_ATTEMPTS = int(os.getenv('MAX_PROCESSING_ATTEMPTS', 3))