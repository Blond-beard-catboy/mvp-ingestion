import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
import threading

# Thread-local storage for correlation_id
_context = threading.local()


class JSONFormatter(logging.Formatter):
    """Форматировщик логов в JSON с поддержкой correlation_id"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Добавляем correlation_id, если есть
        correlation_id = get_correlation_id()
        if correlation_id:
            log_record['correlation_id'] = correlation_id
        
        # Добавляем event_id, если есть в extra
        if hasattr(record, 'event_id'):
            log_record['event_id'] = record.event_id
        
        # Добавляем exception info если есть
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Добавляем extra поля
        if hasattr(record, 'extra'):
            log_record.update(record.extra)
        
        return json.dumps(log_record, ensure_ascii=False)


def set_correlation_id(cid: str) -> None:
    """Установка correlation_id для текущего потока"""
    _context.correlation_id = cid


def get_correlation_id() -> str:
    """Получение correlation_id из текущего потока"""
    return getattr(_context, 'correlation_id', None)


def clear_correlation_id() -> None:
    """Очистка correlation_id для текущего потока"""
    if hasattr(_context, 'correlation_id'):
        delattr(_context, 'correlation_id')


def setup_logging(name: str, level: str = "INFO", json_format: bool = False) -> logging.Logger:
    """
    Настройка логгера для модуля
    
    Args:
        name: Имя логгера (обычно __name__)
        level: Уровень логирования
        json_format: Использовать JSON формат
    
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Если уже есть обработчики, не добавляем новые
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        if json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s [%(correlation_id)s] %(name)s %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
