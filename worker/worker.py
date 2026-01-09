import sys
import os
import logging
import signal
import time
from typing import Optional
# from config import Config

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pika
from worker.config import Config
from shared.rabbit import RabbitMQConsumer
from shared.db_postgres import PostgresClient
from shared.db_mysql import MySQLClient  # НОВОЕ: импорт MySQL клиента
from worker.handlers import handle_event

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class EventWorker:
    """Воркер для обработки событий из RabbitMQ"""
    
    def __init__(self):
        self.config = Config()
        self.running = False
        self.rabbit_consumer: Optional[RabbitMQConsumer] = None
        self.pg_client: Optional[PostgresClient] = None
        self.mysql_client: Optional[MySQLClient] = None  # НОВОЕ: клиент MySQL
        
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        if self.rabbit_consumer:
            self.rabbit_consumer.close()
        
        if self.pg_client:
            self.pg_client.close()
        
        if self.mysql_client:
            self.mysql_client.close()
    
    def connect_to_services(self):
        """Подключение к RabbitMQ, PostgreSQL и MySQL"""
        logger.info("Connecting to services...")
        
        # Подключаемся к PostgreSQL (source of truth)
        try:
            self.pg_client = PostgresClient(self.config.POSTGRES_URL)
            self.pg_client.connect()
            logger.info("✅ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
        
        # НОВОЕ: Подключаемся к MySQL (best-effort проекция)
        if self.config.MYSQL_URL:
            try:
                self.mysql_client = MySQLClient(self.config.MYSQL_URL)
                self.mysql_client.connect()
                logger.info("✅ Connected to MySQL (projection)")
            except Exception as e:
                # MySQL НЕ обязателен для работы воркера
                logger.warning(f"⚠️  Failed to connect to MySQL (projection will be skipped): {e}")
                self.mysql_client = None
        else:
            logger.warning("⚠️  MYSQL_URL not set, MySQL projection disabled")
        
        # Подключаемся к RabbitMQ
        try:
            self.rabbit_consumer = RabbitMQConsumer(self.config.RABBIT_URL)
            self.rabbit_consumer.connect()
            logger.info("✅ Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    def process_message(self, ch, method, properties, body):
        """
        Обработка сообщения из RabbitMQ
        
        Args:
            ch: Канал RabbitMQ
            method: Метод доставки
            properties: Свойства сообщения
            body: Тело сообщения
        """
        logger.debug(f"Received message with delivery tag: {method.delivery_tag}")
        
        try:
            # Обрабатываем событие с передачей обоих клиентов
            success = handle_event(body, self.pg_client, self.mysql_client)
            
            if success:
                # Подтверждаем успешную обработку (только если PostgreSQL записан)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.debug(f"Message acknowledged: {method.delivery_tag}")
            else:
                # Отклоняем сообщение (уйдёт в DLQ)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                logger.warning(f"Message rejected (sent to DLQ): {method.delivery_tag}")
                
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}")
            # Отклоняем сообщение при любой неожиданной ошибке
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def run(self):
        """Основной цикл работы воркера"""
        logger.info("Starting Event Worker...")
        logger.info("Architecture: PostgreSQL (source of truth) + MySQL (best-effort projection)")
        self.setup_signal_handlers()
        self.running = True
        
        while self.running:
            try:
                # Подключаемся к сервисам
                self.connect_to_services()
                
                # Настраиваем обработку сообщений
                if self.rabbit_consumer.channel:
                    # Ограничиваем количество неподтверждённых сообщений
                    self.rabbit_consumer.channel.basic_qos(
                        prefetch_count=self.config.WORKER_PREFETCH_COUNT
                    )
                    
                    # Начинаем слушать очередь
                    self.rabbit_consumer.channel.basic_consume(
                        queue=self.config.RABBIT_QUEUE_EVENTS,
                        on_message_callback=self.process_message,
                        auto_ack=False  # Важно: ручное подтверждение!
                    )
                    
                    logger.info(f"✅ Worker started, listening to queue: {self.config.RABBIT_QUEUE_EVENTS}")
                    logger.info(f"✅ MySQL projection: {'ENABLED' if self.mysql_client else 'DISABLED'}")
                    logger.info("Press Ctrl+C to stop")
                    
                    # Запускаем бесконечный цикл обработки
                    self.rabbit_consumer.channel.start_consuming()
                    
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(f"RabbitMQ connection error: {e}")
                if self.running:
                    logger.info(f"Reconnecting in {self.config.WORKER_RECONNECT_DELAY} seconds...")
                    time.sleep(self.config.WORKER_RECONNECT_DELAY)
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if self.running:
                    logger.info(f"Restarting in {self.config.WORKER_RECONNECT_DELAY} seconds...")
                    time.sleep(self.config.WORKER_RECONNECT_DELAY)
                    
            finally:
                # Закрываем соединения
                if self.rabbit_consumer:
                    self.rabbit_consumer.close()
                    self.rabbit_consumer = None
                
                if self.pg_client:
                    self.pg_client.close()
                    self.pg_client = None
                
                if self.mysql_client:
                    self.mysql_client.close()
                    self.mysql_client = None
        
        logger.info("Worker stopped")

    def stop(self):
        """Остановка воркера"""
        self.running = False
        logger.info("Stopping worker...")


def main():
    """Точка входа"""
    worker = EventWorker()
    
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        raise
    finally:
        worker.stop()


if __name__ == '__main__':
    main()