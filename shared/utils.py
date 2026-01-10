import time
import logging
from typing import Callable, Any, Type, Tuple, Union, Optional
from functools import wraps
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


def generate_event_id() -> str:
    """Генерация UUID для события"""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """Текущее время в UTC"""
    return datetime.now(timezone.utc)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    logger_name: Optional[str] = None
):
    """
    Декоратор для повторных попыток выполнения функции с экспоненциальным backoff
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для увеличения задержки
        exceptions: Исключения, которые триггерят повторную попытку
        logger_name: Имя логгера для логирования попыток
    
    Returns:
        Декоратор функции
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_logger = logging.getLogger(logger_name) if logger_name else logger
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    if attempt > 1:
                        retry_logger.info(
                            f"Retry attempt {attempt}/{max_attempts} for {func.__name__}"
                        )
                    
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        retry_logger.error(
                            f"Failed after {max_attempts} attempts for {func.__name__}: {e}"
                        )
                        raise
                    
                    # Рассчитываем задержку с экспоненциальным backoff
                    current_delay = delay * (backoff ** (attempt - 1))
                    retry_logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: "
                        f"{type(e).__name__}: {e}. Retrying in {current_delay:.2f}s..."
                    )
                    
                    time.sleep(current_delay)
            
            # Это не должно происходить, но для безопасности
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Function {func.__name__} failed without exception")
        
        return wrapper
    return decorator


def is_retryable_error(error: Exception) -> bool:
    """
    Проверяет, является ли ошибка retryable
    
    Args:
        error: Проверяемое исключение
    
    Returns:
        True если ошибка retryable
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Список retryable условий
    retryable_conditions = [
        # Сетевые ошибки
        'connection', 'timeout', 'refused', 'reset',
        'network', 'socket', 'host', 'port',
        
        # Временные ошибки БД
        'deadlock', 'lock wait timeout', 'too many connections',
        'server has gone away', 'lost connection',
        
        # Ошибки ресурсов
        'resource temporarily unavailable', 'temporary failure',
        
        # HTTP/AMQP ошибки
        '503', '504',  # Service Unavailable, Gateway Timeout
    ]
    
    # Проверяем по условиям
    for condition in retryable_conditions:
        if condition in error_str:
            return True
    
    # Проверяем по типу исключения
    retryable_types = [
        'ConnectionError', 'TimeoutError', 'Timeout',
        'ConnectionRefusedError', 'ConnectionResetError',
    ]
    
    if error_type in retryable_types:
        return True
    
    return False


class RetryConfig:
    """Конфигурация для повторных попыток"""
    
    @staticmethod
    def for_mysql():
        """Конфигурация для MySQL операций"""
        return {
            'max_attempts': 3,
            'delay': 1.0,
            'backoff': 2.0,
            'exceptions': (Exception,),
            'logger_name': 'mysql_retry'
        }
    
    @staticmethod
    def for_rabbitmq():
        """Конфигурация для RabbitMQ операций"""
        return {
            'max_attempts': 5,
            'delay': 2.0,
            'backoff': 1.5,
            'exceptions': (Exception,),
            'logger_name': 'rabbitmq_retry'
        }
    
    @staticmethod
    def for_postgres():
        """Конфигурация для PostgreSQL операций"""
        return {
            'max_attempts': 3,
            'delay': 0.5,
            'backoff': 2.0,
            'exceptions': (Exception,),
            'logger_name': 'postgres_retry'
        }