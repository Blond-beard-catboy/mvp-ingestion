from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
from .utils import now_utc


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

    @validator('occurred_at')
    def validate_occurred_at(cls, v):
        """Убедимся, что время не в будущем (с запасом 5 минут)"""
        if v > now_utc():
            if (v - now_utc()).total_seconds() > 300:  # 5 минут
                raise ValueError('occurred_at не может быть более чем на 5 минут в будущем')
        return v