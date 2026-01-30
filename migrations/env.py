import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Указываем, что мы не используем модели SQLAlchemy
target_metadata = None

# Получаем URL из переменных окружения
def get_database_url():
    # Пробуем получить из переменных окружения
    postgres_url = os.environ.get('POSTGRES_URL')
    
    if not postgres_url:
        # Пробуем альтернативные имена переменных
        postgres_url = os.environ.get('DATABASE_URL')
    
    if not postgres_url:
        raise RuntimeError(
            "POSTGRES_URL or DATABASE_URL environment variable is not set. "
            "Example: postgresql://postgres:postgres@localhost:5432/events_db"
        )
    
    return postgres_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Получаем конфигурацию из alembic.ini
    configuration = config.get_section(config.config_ini_section)
    
    if configuration is None:
        configuration = {}
    
    # Переопределяем URL из переменных окружения
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()