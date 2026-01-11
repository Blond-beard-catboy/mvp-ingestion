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
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "plain")  # 'plain' или 'json'
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'
    
    JSON_LOGS = os.environ.get('JSON_LOGS', 'true').lower() == 'true'

    # Ограничения
    MAX_BODY_BYTES = int(os.getenv('MAX_BODY_BYTES', 1000000))