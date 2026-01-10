import json
import logging
import time
from typing import Dict, Any
from datetime import datetime

from shared.models import IncomingEvent
from shared.db_postgres import PostgresClient
from shared.db_mysql import MySQLClient
from shared.utils import retry, RetryConfig, is_retryable_error

logger = logging.getLogger(__name__)


def handle_event_with_retry(
    message_body: bytes,
    pg_client: PostgresClient,
    mysql_client: MySQLClient = None
) -> bool:
    """
    Обработка события с retry для MySQL
    
    Args:
        message_body: Тело сообщения из RabbitMQ
        pg_client: Клиент PostgreSQL
        mysql_client: Клиент MySQL (опционально)
        
    Returns:
        bool: True если событие успешно обработано
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
        
        # Сохраняем в PostgreSQL (source of truth) - БЕЗ RETRY (критично)
        inserted = pg_client.insert_event(event_dict)
        
        if inserted:
            logger.info(f"Event saved to PostgreSQL: {event.event_id}")
        else:
            logger.info(f"Event already exists (idempotency): {event.event_id}")
        
        # BEST-EFFORT с RETRY: Пытаемся сохранить в MySQL проекцию
        if mysql_client:
            _attempt_mysql_projection_with_retry(event_dict, mysql_client)
        else:
            logger.debug("MySQL client not available, skipping projection")
        
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        return False


def _attempt_mysql_projection_with_retry(event_dict: Dict[str, Any], mysql_client: MySQLClient):
    """
    Попытка сохранения в MySQL с повторными попытками
    
    Args:
        event_dict: Данные события
        mysql_client: Клиент MySQL
    """
    event_id = event_dict.get('event_id', 'unknown')
    max_attempts = 3
    delay = 1.0
    backoff = 2.0
    
    for attempt in range(1, max_attempts + 1):
        try:
            start_time = time.time()
            mysql_success = mysql_client.upsert_projection(event_dict)
            duration = time.time() - start_time
            
            if mysql_success:
                logger.info(f"Event projection saved to MySQL (attempt {attempt}/{max_attempts}): {event_id} ({duration:.3f}s)")
                return True
            else:
                logger.warning(f"MySQL projection failed (non-retryable, attempt {attempt}): {event_id}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            
            if is_retryable_error(e) and attempt < max_attempts:
                wait_time = delay * (backoff ** (attempt - 1))
                logger.warning(
                    f"MySQL projection retryable error (attempt {attempt}/{max_attempts}): "
                    f"{type(e).__name__}: {e}. Waiting {wait_time:.1f}s ({duration:.3f}s)"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"MySQL projection failed (attempt {attempt}/{max_attempts}): "
                    f"{type(e).__name__}: {e} ({duration:.3f}s)"
                )
                return False
    
    return False


def handle_event(
    message_body: bytes,
    pg_client: PostgresClient,
    mysql_client: MySQLClient = None
) -> bool:
    """
    Обработка одного события (совместимость с существующим кодом)
    """
    return handle_event_with_retry(message_body, pg_client, mysql_client)