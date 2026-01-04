-- Заменим UUID на VARCHAR(255) для event_id
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,           -- ИЗМЕНЕНО: VARCHAR вместо UUID
    schema_version INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Остальные индексы и комментарии остаются прежними
CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);

-- Комментарии...
COMMENT ON TABLE events IS 'Таблица для хранения входящих событий';
COMMENT ON COLUMN events.event_id IS 'Уникальный идентификатор события (строка)';  -- ИЗМЕНЕНО
COMMENT ON COLUMN events.schema_version IS 'Версия схемы события';
COMMENT ON COLUMN events.event_type IS 'Тип события (например: user_signup, payment_received)';
COMMENT ON COLUMN events.source IS 'Источник события (например: mobile_app, web_backend)';
COMMENT ON COLUMN events.occurred_at IS 'Время возникновения события в системе-источнике';
COMMENT ON COLUMN events.payload IS 'Тело события в формате JSONB';
COMMENT ON COLUMN events.created_at IS 'Время создания записи в БД';
COMMENT ON COLUMN events.updated_at IS 'Время последнего обновления записи';