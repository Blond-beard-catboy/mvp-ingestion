from pydantic import BaseModel, Field, validator
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4
import json


class IncomingEvent(BaseModel):
    """Модель входящего события от клиента"""
    event_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="UUID события. Если не указан, сгенерируется автоматически"
    )
    schema_version: int = Field(
        ge=1,
        description="Версия схемы события. Должна быть >= 1"
    )
    event_type: str = Field(
        min_length=1,
        max_length=100,
        description="Тип события (например, 'user_signup', 'payment_received')"
    )
    source: str = Field(
        min_length=1,
        max_length=100,
        description="Источник события (например, 'mobile_app', 'web_backend')"
    )
    occurred_at: datetime = Field(
        description="Время возникновения события в ISO 8601"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Тело события (произвольный JSON)"
    )

    @validator('occurred_at', pre=True)
    def validate_occurred_at_format(cls, v):
        """Унифицируем формат времени"""
        if isinstance(v, str):
            # Убираем 'Z' если есть
            v = v.rstrip('Z')
            try:
                # Парсим строку
                dt = datetime.fromisoformat(v)
                # Если нет временной зоны, добавляем UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                raise ValueError('Неверный формат времени. Используйте ISO 8601 (например: 2024-01-15T10:30:00)')
        return v
    
    @validator('occurred_at')
    def check_occurred_at_not_in_future(cls, v):
        """Убедимся, что время не в будущем (с запасом 5 минут)"""
        now = datetime.now(timezone.utc)
        
        # Если v без временной зоны (offset-naive), добавляем UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        
        # Если v с временной зоной, конвертируем в UTC
        else:
            v = v.astimezone(timezone.utc)
        
        if v > now:
            if (v - now).total_seconds() > 300:  # 5 минут
                raise ValueError('occurred_at не может быть более чем на 5 минут в будущем')
        return v

    def dict_for_rabbitmq(self) -> dict:
        """Сериализация для отправки в RabbitMQ"""
        data = self.dict()
        # Конвертируем datetime в строку без временной зоны
        if isinstance(data.get('occurred_at'), datetime):
            # Убираем временную зону для совместимости
            dt = data['occurred_at']
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            data['occurred_at'] = dt.isoformat()
        return data

    def serialize_to_json(self) -> bytes:
        """Сериализация события в JSON bytes для отправки в RabbitMQ"""
        return json.dumps(self.dict_for_rabbitmq()).encode('utf-8')

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }