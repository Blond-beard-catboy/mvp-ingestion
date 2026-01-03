import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Форматировщик логов в JSON"""
    
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
        
        # Добавляем exception info если есть
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Добавляем extra поля
        if hasattr(record, 'extra'):
            log_record.update(record.extra)
        
        return json.dumps(log_record, ensure_ascii=False)


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
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger