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

```

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
```

## ✅ Результаты Дня 3

### Успешно выполнено:

1. **✅ Создана таблица `events` в PostgreSQL**:
   - Колонка `event_id` типа VARCHAR для гибкости
   - Поддержка JSONB для хранения payload
   - Индексы для быстрого поиска
   - Комментарии к таблице и колонкам

2. **✅ Реализована идемпотентность через SQL**:
   - Используется `ON CONFLICT (event_id) DO NOTHING`
   - Одинаковые `event_id` не дублируются
   - Безопасные повторные попытки вставки

3. **✅ Создан клиент PostgreSQL**:
   - Автоматическое подключение и переподключение
   - Поддержка идемпотентных операций
   - Логирование всех действий

4. **✅ Протестирована работа**:
   - Идемпотентность работает корректно
   - Уникальные события успешно вставляются
   - Формат времени обрабатывается правильно

### Проверка работы:

```bash
# Применить схему
./scripts/apply_sql_postgres.sh

# Запустить тест идемпотентности
python scripts/test_idempotency.py

# Проверить вручную
psql $POSTGRES_URL -c "SELECT COUNT(*) FROM events;"
    ```

