-- Создание таблицы проекций событий
CREATE TABLE IF NOT EXISTS events_projection (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    occurred_at DATETIME NOT NULL,
    payload JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_id (event_id),
    INDEX idx_created_at (created_at),
    INDEX idx_event_type (event_type),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Комментарии к таблице
ALTER TABLE events_projection 
    COMMENT = 'Проекция событий для быстрого чтения (best-effort replication)';