-- Этот файл будет выполнен при инициализации PostgreSQL
-- Создаем базу данных
CREATE DATABASE events_db;

-- Даем права пользователю events_user (создается автоматически через переменные окружения)
GRANT ALL PRIVILEGES ON DATABASE events_db TO events_user;
