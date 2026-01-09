import json
import logging
from datetime import datetime
from typing import Dict, Any

from shared.models import IncomingEvent
from shared.db_postgres import PostgresClient
from shared.db_mysql import MySQLClient

logger = logging.getLogger(__name__)


def handle_event(message_body: bytes, pg_client: PostgresClient, mysql_client: MySQLClient = None) -> bool:
    """
    Обработка одного события
    
    Args:
        message_body: Тело сообщения из RabbitMQ (bytes)
        pg_client: Клиент PostgreSQL
        mysql_client: Клиент MySQL (опционально, для проекции)
        
    Returns:
        bool: True если событие успешно обработано, False если ошибка
    """
    try:
        # Парсим JSON
        message_str = message_body.decode('utf-8')
        raw_data = json.loads(message_str)
        
        # Валидируем через Pydantic модель
        event = IncomingEvent(**raw_data)
        
        logger.info(f"Processing event: {event.event_id}, type: {event.event_type}")
        
        # Подготавливаем данные для PostgreSQL
        event_dict = event.dict()
        
        # Сохраняем в PostgreSQL (source of truth)
        inserted = pg_client.insert_event(event_dict)
        
        if inserted:
            logger.info(f"Event saved to PostgreSQL: {event.event_id}")
        else:
            logger.info(f"Event already exists (idempotency): {event.event_id}")
        
        # BEST-EFFORT: Пытаемся сохранить в MySQL проекцию
        if mysql_client:
            try:
                mysql_success = mysql_client.upsert_projection(event_dict)
                if mysql_success:
                    logger.info(f"Event projection saved to MySQL: {event.event_id}")
                else:
                    logger.warning(f"Failed to save event projection to MySQL: {event.event_id}")
                    # НЕ ПРЕРЫВАЕМ ВЫПОЛНЕНИЕ!
                    # MySQL проекция - best-effort, продолжаем работу
            except Exception as e:
                logger.error(f"MySQL projection error (non-critical): {e}", exc_info=False)
                # НЕ ПРЕРЫВАЕМ ВЫПОЛНЕНИЕ!
        else:
            logger.debug("MySQL client not available, skipping projection")
        
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        return False


def validate_event(event_data: Dict[str, Any]) -> bool:
    """
    Базовая валидация события
    
    Args:
        event_data: Словарь с данными события
        
    Returns:
        bool: True если событие валидно
    """
    required_fields = ['event_id', 'schema_version', 'event_type', 'source', 'occurred_at']
    
    for field in required_fields:
        if field not in event_data:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Проверяем, что event_id - строка
    if not isinstance(event_data.get('event_id'), str):
        logger.error("event_id must be a string")
        return False
    
    # Проверяем, что schema_version - число
    if not isinstance(event_data.get('schema_version'), int):
        logger.error("schema_version must be an integer")
        return False
    
    return True