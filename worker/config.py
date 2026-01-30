import os

class Config:
    # RabbitMQ
    RABBIT_URL = os.environ.get('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
    RABBIT_QUEUE_EVENTS = os.environ.get('RABBIT_QUEUE_EVENTS', 'events')
    RABBIT_QUEUE_DLQ = os.environ.get('RABBIT_QUEUE_DLQ', 'events.dlq')
    
    # Databases
    POSTGRES_URL = os.environ.get('POSTGRES_URL', 'postgresql://events_user:password@localhost:5432/events_db')
    MYSQL_URL = os.environ.get('MYSQL_URL', 'mysql://root:root@localhost:3306/events_projection')
    
    # Worker settings
    WORKER_PREFETCH_COUNT = int(os.environ.get('WORKER_PREFETCH_COUNT', 1))
    WORKER_RECONNECT_DELAY = int(os.environ.get('WORKER_RECONNECT_DELAY', 5))
    MAX_PROCESSING_ATTEMPTS = int(os.environ.get('MAX_PROCESSING_ATTEMPTS', 3))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    JSON_LOGS = os.environ.get('JSON_LOGS', 'true').lower() == 'true'
