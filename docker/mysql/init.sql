-- Создание базы данных проекций (будет использоваться в День 7)
CREATE DATABASE IF NOT EXISTS events_projection;
USE events_projection;

-- Таблица проекций событий (предварительная структура)
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
    INDEX idx_event_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Права для пользователя
GRANT ALL PRIVILEGES ON events_projection.* TO 'events_user'@'%';
FLUSH PRIVILEGES;