# MVP Ingestion Service

Минимальный сервис приёма событий с гарантированной доставкой.

## Архитектура
- **API** (Flask): приём событий, валидация
- **Worker** (Celery/RabbitMQ): асинхронная обработка (будет добавлен)
- **PostgreSQL/MySQL**: хранение событий (будет добавлено)

## Быстрый старт

### 1. Настройка окружения
```bash
# Клонируй репозиторий
git clone <repo-url>
cd mvp-ingestion

# Создай виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установи зависимости API
pip install -r api/requirements.txt

# Скопируй конфигурацию
cp .env.example .env
# Отредактируй .env при необходимости

## Day 2: RabbitMQ Producer

### Требования
Для работы Day 2 требуется RabbitMQ.

#### Установка RabbitMQ:

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Включить web-интерфейс (опционально)
sudo rabbitmq-plugins enable rabbitmq_management