import os

class Config:
    # RabbitMQ
    RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672")
    RABBIT_QUEUE_EVENTS = os.getenv("RABBIT_QUEUE_EVENTS", "events")
    RABBIT_QUEUE_DLQ = os.getenv("RABBIT_QUEUE_DLQ", "events.dlq")
    
    # PostgreSQL
    POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://events_user:password@localhost:5432/events_db")
    
    # MySQL
    MYSQL_URL = os.getenv("MYSQL_URL", "mysql://events_user:password@localhost:3306/events_projection")
    
    # Worker settings
    WORKER_PREFETCH_COUNT = int(os.getenv("WORKER_PREFETCH_COUNT", "1"))
    WORKER_RECONNECT_DELAY = int(os.getenv("WORKER_RECONNECT_DELAY", "5"))
    MAX_PROCESSING_ATTEMPTS = int(os.getenv("MAX_PROCESSING_ATTEMPTS", "3"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "plain")  # 'plain' или 'json'
