-- Создание таблицы events если не существует
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    schema_version INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Создание индексов если не существуют
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_event_id') THEN
        CREATE INDEX idx_events_event_id ON events(event_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_created_at') THEN
        CREATE INDEX idx_events_created_at ON events(created_at);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_event_type') THEN
        CREATE INDEX idx_events_event_type ON events(event_type);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_events_source') THEN
        CREATE INDEX idx_events_source ON events(source);
    END IF;
END $$;

-- Комментарии к таблице
COMMENT ON TABLE events IS 'Таблица для хранения входящих событий';
COMMENT ON COLUMN events.event_id IS 'Уникальный идентификатор события (строка)';
COMMENT ON COLUMN events.schema_version IS 'Версия схемы события';
COMMENT ON COLUMN events.event_type IS 'Тип события';
COMMENT ON COLUMN events.source IS 'Источник события';
COMMENT ON COLUMN events.occurred_at IS 'Время возникновения события в системе-источнике';
COMMENT ON COLUMN events.payload IS 'Тело события в формате JSONB';
COMMENT ON COLUMN events.created_at IS 'Время создания записи в БД';
COMMENT ON COLUMN events.updated_at IS 'Время последнего обновления записи';