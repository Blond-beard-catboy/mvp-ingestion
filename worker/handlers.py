import json
import logging
import time
from typing import Dict, Any
from pydantic import ValidationError

from shared.models import IncomingEvent
from shared.db_postgres import PostgresClient
from shared.db_mysql import MySQLClient
from shared.utils import is_retryable_error
from shared.logging import get_correlation_id

logger = logging.getLogger(__name__)


def handle_event_with_dlq(message_body: bytes, pg_client: PostgresClient, 
                         mysql_client: MySQLClient = None, rabbit_url: str = None) -> bool:
    """
    Обработка события с отправкой невалидных сообщений в DLQ
    
    Args:
        message_body: Тело сообщения
        pg_client: Клиент PostgreSQL
        mysql_client: Клиент MySQL
        rabbit_url: URL RabbitMQ для отправки в DLQ
    
    Returns:
        bool: True если успешно, False если отправлено в DLQ
    """
    correlation_id = get_correlation_id()  # Получаем correlation_id
    
    try:
        # Парсинг JSON
        message_str = message_body.decode('utf-8')
        raw_data = json.loads(message_str)
        
        # Валидация
        event = IncomingEvent(**raw_data)
        event_dict = event.dict()
        
        # Логируем с correlation_id
        logger.info(
            f"Processing event: {event.event_id}, type: {event.event_type}, "
            f"correlation: {correlation_id}",
            extra={'event_id': event.event_id, 'correlation_id': correlation_id}
        )
        
        # Запись в PostgreSQL
        inserted = pg_client.insert_event(event_dict)
        
        if inserted:
            logger.info(f"Event saved to PostgreSQL: {event.event_id}, correlation: {correlation_id}")
        else:
            logger.info(f"Event already exists: {event.event_id}, correlation: {correlation_id}")
        
        # MySQL проекция (best-effort)
        if mysql_client:
            _attempt_mysql_projection_with_retry(event_dict, mysql_client, correlation_id)
        
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}, correlation: {correlation_id}")
        if rabbit_url:
            _send_to_dlq(message_body, rabbit_url, {
                "reason": "invalid_json",
                "error": str(e),
                "exception_type": "JSONDecodeError",
                "correlation_id": correlation_id
            })
        return False
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}, correlation: {correlation_id}")
        if rabbit_url:
            _send_to_dlq(message_body, rabbit_url, {
                "reason": "validation_error",
                "error": str(e),
                "exception_type": "ValidationError",
                "errors": e.errors() if hasattr(e, 'errors') else None,
                "correlation_id": correlation_id
            })
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}, correlation: {correlation_id}")
        if rabbit_url:
            _send_to_dlq(message_body, rabbit_url, {
                "reason": "unexpected_error",
                "error": str(e),
                "exception_type": type(e).__name__,
                "correlation_id": correlation_id
            })
        return False


def _attempt_mysql_projection_with_retry(event_dict: Dict[str, Any], mysql_client: MySQLClient, correlation_id: str = None):
    """
    Попытка сохранения в MySQL с повторными попытками
    
    Args:
        event_dict: Данные события
        mysql_client: Клиент MySQL
        correlation_id: Correlation ID для логирования
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
                logger.info(f"Event projection saved to MySQL (attempt {attempt}/{max_attempts}): {event_id} ({duration:.3f}s), correlation: {correlation_id}")
                return True
            else:
                logger.warning(f"MySQL projection failed (non-retryable, attempt {attempt}): {event_id}, correlation: {correlation_id}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            
            if is_retryable_error(e) and attempt < max_attempts:
                wait_time = delay * (backoff ** (attempt - 1))
                logger.warning(
                    f"MySQL projection retryable error (attempt {attempt}/{max_attempts}): "
                    f"{type(e).__name__}: {e}. Waiting {wait_time:.1f}s ({duration:.3f}s), correlation: {correlation_id}"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"MySQL projection failed (attempt {attempt}/{max_attempts}): "
                    f"{type(e).__name__}: {e} ({duration:.3f}s), correlation: {correlation_id}"
                )
                return False
    
    return False


def _send_to_dlq(message_body: bytes, rabbit_url: str, error_info: dict):
    """Вспомогательная функция для отправки в DLQ"""
    try:
        from shared.rabbit import publish_to_dlq
        publish_to_dlq(rabbit_url, message_body, error_info)
        logger.info(f"Message sent to DLQ: {error_info['reason']}, correlation: {error_info.get('correlation_id')}")
    except Exception as dlq_error:
        logger.error(f"Failed to send to DLQ: {dlq_error}, correlation: {error_info.get('correlation_id')}")


def handle_event_with_retry(
    message_body: bytes,
    pg_client: PostgresClient,
    mysql_client: MySQLClient = None
) -> bool:
    """
    Обработка события с retry для MySQL (совместимость с существующим кодом)
    
    Args:
        message_body: Тело сообщения из RabbitMQ
        pg_client: Клиент PostgreSQL
        mysql_client: Клиент MySQL (опционально)
        
    Returns:
        bool: True если событие успешно обработано
    """
    correlation_id = get_correlation_id()
    
    try:
        # Парсим JSON
        message_str = message_body.decode('utf-8')
        raw_data = json.loads(message_str)
        
        # Валидируем через Pydantic модель
        event = IncomingEvent(**raw_data)
        
        logger.info(f"Processing event: {event.event_id}, type: {event.event_type}, correlation: {correlation_id}")
        
        # Подготавливаем данные для PostgreSQL
        event_dict = event.dict()
        
        # Сохраняем в PostgreSQL (source of truth)
        inserted = pg_client.insert_event(event_dict)
        
        if inserted:
            logger.info(f"Event saved to PostgreSQL: {event.event_id}, correlation: {correlation_id}")
        else:
            logger.info(f"Event already exists (idempotency): {event.event_id}, correlation: {correlation_id}")
        
        # BEST-EFFORT с RETRY: Пытаемся сохранить в MySQL проекцию
        if mysql_client:
            _attempt_mysql_projection_with_retry(event_dict, mysql_client, correlation_id)
        else:
            logger.debug(f"MySQL client not available, skipping projection, correlation: {correlation_id}")
        
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}, correlation: {correlation_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to process event: {e}, correlation: {correlation_id}")
        return False