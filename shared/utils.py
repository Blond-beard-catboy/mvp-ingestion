import uuid
from datetime import datetime, timezone


def generate_event_id() -> str:
    """Генерация UUID для события"""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """Текущее время в UTC"""
    return datetime.now(timezone.utc)