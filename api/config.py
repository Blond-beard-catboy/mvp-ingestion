import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'
    MAX_BODY_BYTES = int(os.getenv('MAX_BODY_BYTES', 1000000))
    RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')