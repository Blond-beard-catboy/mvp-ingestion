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

## День 4 — Worker v1: Потребление и сохранение событий

### Цель
Создать воркер, который читает события из RabbitMQ, валидирует их и сохраняет в PostgreSQL.

### Запуск воркера

#### 1. Установите зависимости:
```bash
pip install -r worker/requirements.txt
```

## 🐳 Docker Compose (День 5)

Для запуска зависимостей через Docker Compose:

### Быстрый старт

```bash
# Запуск всех сервисов
./scripts/docker-compose-up.sh

# Проверка состояния
./scripts/check-docker-services.sh

# Остановка
./scripts/docker-compose-down.sh
```

## 🐳 Полная контейнеризация (День 6)

### Запуск всего проекта одной командой

```bash
# Запуск всех 5 сервисов
./scripts/docker-full-up.sh

# Или вручную
docker-compose up --build -d
```

## День 7 — MySQL Projection (Best-Effort)

### Архитектура

Клиент -> API -> RabbitMQ -> Worker -> PostgreSQL (source of truth) -> MySQL (best-effort projection)


### Концепция

- **PostgreSQL** — основной источник истины (source of truth)
  - Всегда получает события первыми
  - Гарантирует идемпотентность через `ON CONFLICT`
  - Критически важен для работы системы

- **MySQL** — проекция для быстрого чтения (projection)
  - Best-effort репликация: если MySQL недоступен, система продолжает работать
  - Используется для аналитики, отчетов, быстрого доступа к данным
  - Данные могут быть неполными (eventual consistency)

### Настройки

```env
# Обязательно
POSTGRES_URL=postgresql://events_user:password@postgres:5432/events_db

# Опционально (система работает и без MySQL)
MYSQL_URL=mysql://events_user:password@mysql:3306/events_projection
```
## 🔄 Retry Policy (День 8)

### Цель
Обеспечить надежную запись в MySQL проекцию при transient (временных) ошибках.

### Реализация
1. **Retry декоратор** в `shared/utils.py`:
   - Экспоненциальный backoff (задержка × 2ⁿ)
   - Конфигурируемые параметры: попытки, задержка, множитель
   - Логирование каждой попытки

2. **Классификация ошибок**:
   - **Retryable**: сетевые ошибки, таймауты, deadlocks, временная недоступность
   - **Non-retryable**: ошибки валидации, синтаксиса, констрейнты

3. **Конфигурации**:
   ```python
   # MySQL операции
   RetryConfig.for_mysql()  # 3 попытки, delay=1s, backoff=2
   
   # RabbitMQ операции  
   RetryConfig.for_rabbitmq()  # 5 попыток, delay=2s, backoff=1.5
   
   # Сетевые операции
   RetryConfig.for_network()  # 3 попытки, delay=0.5s, backoff=2
   ```

## 💀 День 9 — DLQ (Dead Letter Queue)

### Назначение
DLQ (Dead Letter Queue) — очередь для сообщений, которые не могут быть обработаны:

1. **Невалидный JSON** — синтаксические ошибки
2. **Ошибки валидации** — нарушение схемы Pydantic
3. **Критические ошибки** — неустранимые сбои при обработке

### Архитектура
```
API → RabbitMQ (events) → Worker → PostgreSQL/MySQL
                    ↓
             RabbitMQ (events.dlq)
```

### Использование

#### Отправка тестового "плохого" сообщения:
```bash
python scripts/seed_bad_message.py
```

#### Чтение DLQ:
```bash
# Просмотреть 10 сообщений
python scripts/read_dlq.py --limit 10

# Сохранить в файл
python scripts/read_dlq.py --limit 20 --save

# Очистить DLQ
python scripts/read_dlq.py --purge
```

#### Тестирование DLQ:
```bash
./scripts/test_dlq.sh
```

### Логирование
Сообщения в DLQ содержат:
- Оригинальное сообщение
- Причину ошибки
- Тип исключения
- Timestamp
- Дополнительную диагностику

### Мониторинг
```bash
# Количество сообщений в DLQ
docker-compose exec rabbitmq rabbitmqctl list_queues name messages

# Web интерфейс
http://localhost:15672/#/queues (guest/guest)
```

### Важно
- Сообщения в DLQ требуют ручного разбора
- DLQ не очищается автоматически
- Частые попадания в DLQ указывают на проблемы с клиентами


### 10. **Тестирование миграций**

```bash
# Останавливаем все контейнеры и удаляем данные
docker-compose down -v

# Запускаем с нуля
docker-compose up --build -d

# Проверяем миграции
docker-compose exec api alembic current
docker-compose exec api alembic history

# Проверяем таблицу
docker-compose exec postgres psql -U postgres -d events_db -c "\dt events"
docker-compose exec postgres psql -U postgres -d events_db -c "\d events"

# Тестируем отправку события
curl -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": 1,
    "event_type": "migration_test",
    "source": "alembic",
    "occurred_at": "2024-01-15T12:00:00Z",
    "payload": {"test": "migration_works"}
  }'

# Проверяем данные в таблице
docker-compose exec postgres psql -U postgres -d events_db -c "SELECT * FROM events;"