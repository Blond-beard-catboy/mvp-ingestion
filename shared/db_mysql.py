from __future__ import annotations
import logging
from typing import Dict, Any, Optional
import json
from datetime import datetime

# Используем mysql-connector-python (официальный драйвер)
try:
    import mysql.connector
    from mysql.connector import Error, pooling
    from mysql.connector.pooling import MySQLConnectionPool
except ImportError:
    mysql = None

logger = logging.getLogger(__name__)


class MySQLClient:
    """Клиент для работы с MySQL с поддержкой пула соединений"""
    
    def __init__(self, connection_url: str):
        """
        Инициализация клиента MySQL
        
        Args:
            connection_url: URL подключения в формате 
                           mysql://user:password@host:port/database
        """
        self.connection_url = connection_url
        self.connection_pool: Optional[pooling.MySQLConnectionPool] = None
        
    def parse_url(self, url: str) -> Dict[str, Any]:
        """Парсинг URL подключения MySQL"""
        # Убираем префикс mysql://
        if url.startswith('mysql://'):
            url = url[8:]
        
        # Разбираем URL на компоненты
        # Формат: user:password@host:port/database
        auth_part, rest = url.split('@') if '@' in url else ('', url)
        host_part, db_part = rest.split('/') if '/' in rest else (rest, '')
        
        user, password = auth_part.split(':') if ':' in auth_part else ('', '')
        
        if ':' in host_part:
            host, port = host_part.split(':')
            port = int(port)
        else:
            host = host_part
            port = 3306
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': db_part
        }
    
    def connect(self):
        """Создание пула соединений с MySQL"""
        if self.connection_pool is not None:
            return
            
        if mysql is None:
            raise ImportError("mysql-connector-python не установлен")
        
        try:
            config = self.parse_url(self.connection_url)
            
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="ingestion_pool",
                pool_size=3,
                pool_reset_session=True,
                **config
            )
            
            logger.info(f"MySQL connection pool created: {config['host']}:{config['port']}/{config['database']}")
            
            # ТЕСТОВОЕ СОЕДИНЕНИЕ - ИСПРАВЛЕННАЯ ВЕРСИЯ
            connection = self.connection_pool.get_connection()
            cursor = None
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()  # ВАЖНО: читаем результат!
                logger.debug(f"Test query result: {result}")
            finally:
                if cursor:
                    cursor.close()
                connection.close()  # Возвращаем соединение в пул
                
        except Error as e:
            logger.error(f"Failed to create MySQL connection pool: {e}")
            raise
    
    def get_connection(self):
        """Получение соединения из пула"""
        if self.connection_pool is None:
            self.connect()
        return self.connection_pool.get_connection()
    
    def upsert_projection(self, event_data: Dict[str, Any]) -> bool:
        """
        Best-effort вставка или обновление события в проекции MySQL
        
        Args:
            event_data: Словарь с данными события
            
        Returns:
            bool: True если операция успешна, False если произошла ошибка
        """
        if mysql is None:
            logger.warning("mysql-connector-python not installed, skipping MySQL projection")
            return False
        
        try:
            self.connect()
            
            # Подготавливаем данные
            event_id = event_data.get('event_id')
            event_type = event_data.get('event_type')
            source = event_data.get('source')
            occurred_at = event_data.get('occurred_at')
            payload = event_data.get('payload', {})
            
            # Преобразуем occurred_at в строку для MySQL
            if isinstance(occurred_at, datetime):
                occurred_at_str = occurred_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Если это строка, пытаемся преобразовать
                occurred_at_str = str(occurred_at)
            
            # Преобразуем payload в JSON
            if isinstance(payload, dict):
                payload_json = json.dumps(payload)
            else:
                payload_json = json.dumps({"raw": str(payload)})
            
            query = """
            INSERT INTO events_projection 
                (event_id, event_type, source, occurred_at, payload)
            VALUES 
                (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                event_type = VALUES(event_type),
                source = VALUES(source),
                occurred_at = VALUES(occurred_at),
                payload = VALUES(payload),
                updated_at = CURRENT_TIMESTAMP
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (event_id, event_type, source, occurred_at_str, payload_json))
                conn.commit()
                cursor.close()
            
            logger.info(f"Event projection upserted in MySQL: {event_id}")
            return True
            
        except Error as e:
            # Классификация ошибок
            error_code = e.errno if hasattr(e, 'errno') else None
            
            # Retryable ошибки (можно попробовать повторить)
            retryable_errors = [
                2003,  # Connection refused
                2006,  # MySQL server has gone away
                2013,  # Lost connection to MySQL server
                1213,  # Deadlock found
            ]
            
            if error_code in retryable_errors:
                logger.warning(f"Retryable MySQL error ({error_code}): {e}")
            else:
                logger.error(f"Non-retryable MySQL error ({error_code}): {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error in MySQL projection: {e}")
            return False
    
    def is_error_retryable(self, error: Exception) -> bool:
        """
        Проверка, является ли ошибка retryable
        
        Args:
            error: Исключение
            
        Returns:
            bool: True если ошибка retryable
        """
        if not hasattr(error, 'errno'):
            return False
            
        retryable_errors = [2003, 2006, 2013, 1213]
        return error.errno in retryable_errors
    
    def close(self):
        """Закрытие пула соединений"""
        if self.connection_pool:
            self.connection_pool.close()
            logger.info("MySQL connection pool closed")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()