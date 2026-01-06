import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PostgresClient:
    """Клиент для работы с PostgreSQL с поддержкой идемпотентности"""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.conn = None
    
    def connect(self):
        """Установка соединения с PostgreSQL"""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    self.connection_url,
                    cursor_factory=RealDictCursor
                )
                logger.info("Connected to PostgreSQL")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                self.conn = None
                raise
    
    def insert_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Вставка события с проверкой идемпотентности
        
        Args:
            event_data: Словарь с данными события
        
        Returns:
            bool: True если событие вставлено, False если уже существует
        """
        self.connect()
        
        # Обрабатываем occurred_at
        occurred_at = event_data.get('occurred_at')
        
        if isinstance(occurred_at, datetime):
            # Если есть временная зона, конвертируем в UTC и затем убираем временную зону
            if occurred_at.tzinfo is not None:
                occurred_at = occurred_at.astimezone(timezone.utc).replace(tzinfo=None)
            occurred_at_str = occurred_at.isoformat()
        else:
            # Если это строка, убираем 'Z' если есть
            occurred_at_str = str(occurred_at).rstrip('Z')
        
        # Для поля payload используем Json адаптер
        payload = event_data.get('payload', {})
        
        query = """
        INSERT INTO events 
            (event_id, schema_version, event_type, source, occurred_at, payload)
        VALUES 
            (%(event_id)s, %(schema_version)s, %(event_type)s, %(source)s, 
             %(occurred_at)s, %(payload)s)
        ON CONFLICT (event_id) 
        DO NOTHING
        RETURNING id;
        """
        
        params = {
            'event_id': event_data.get('event_id'),
            'schema_version': event_data.get('schema_version'),
            'event_type': event_data.get('event_type'),
            'source': event_data.get('source'),
            'occurred_at': occurred_at_str,
            'payload': Json(payload)
        }
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                self.conn.commit()
                
                if result:
                    logger.info(f"Event inserted: {event_data.get('event_id')}")
                    return True
                else:
                    logger.info(f"Event already exists: {event_data.get('event_id')}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to insert event: {e}")
            self.conn.rollback()
            raise
    
    def close(self):
        """Закрытие соединения с PostgreSQL"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.debug("PostgreSQL connection closed")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()