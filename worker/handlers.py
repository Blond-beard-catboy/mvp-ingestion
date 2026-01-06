import json
import logging
from datetime import datetime
from typing import Dict, Any

from shared.models import IncomingEvent
from shared.db_postgres import PostgresClient

logger = logging.getLogger(__name__)


def handle_event(message_body: bytes, pg_client: PostgresClient) -> bool:
    """
    Обработка одного события
    
    Args:
        message_body: Тело сообщения из RabbitMQ (bytes)
        pg_client: Клиент PostgreSQL
        
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
        
        # Преобразуем occurred_at в правильный формат (убираем 'Z')
        # occurred_at = event_dict.get('occurred_at')
        # if isinstance(occurred_at, str) and occurred_at.endswith('Z'):
        #     event_dict['occurred_at'] = occurred_at[:-1]
        
        # Сохраняем в PostgreSQL
        inserted = pg_client.insert_event(event_dict)
        
        if inserted:
            logger.info(f"Event saved to PostgreSQL: {event.event_id}")
        else:
            logger.info(f"Event already exists (idempotency): {event.event_id}")
        
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