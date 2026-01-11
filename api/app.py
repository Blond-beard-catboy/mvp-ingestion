import sys
import os
import json
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify, g
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from shared.logging import set_correlation_id, get_correlation_id

from shared.models import IncomingEvent
from shared.logging import setup_logging
from shared.rabbit import RabbitMQProducer
from api.config import Config

app = Flask(__name__)
app.config.from_object(Config)
logger = setup_logging(__name__, Config.LOG_LEVEL, json_format=Config.JSON_LOGS)

# Инициализация RabbitMQ продюсера
rabbit_producer = RabbitMQProducer(Config.RABBIT_URL)


@app.before_request
def before_request():
    """Установка correlation_id для каждого запроса"""
    # Берем из заголовка или генерируем новый
    correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    set_correlation_id(correlation_id)
    g.correlation_id = correlation_id


@app.after_request
def after_request(response):
    """Добавляем correlation_id в заголовки ответа"""
    correlation_id = get_correlation_id()
    if correlation_id:
        response.headers['X-Correlation-ID'] = correlation_id
    return response


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса"""
    # Проверяем подключение к RabbitMQ
    try:
        rabbit_producer.connect()
        rabbit_status = "connected"
    except Exception as e:
        logger.warning(f"RabbitMQ health check failed: {e}")
        rabbit_status = "disconnected"
    
    return jsonify({
        "status": "healthy",
        "service": "ingestion-api",
        "rabbitmq": rabbit_status
    })


@app.route('/events', methods=['POST'])
def receive_event():
    """Приём события от клиента"""
    correlation_id = get_correlation_id()  # Получаем correlation_id
    
    if not request.is_json:
        raise BadRequest("Content-Type must be application/json")
    
    try:
        raw_data = request.get_json(force=True)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON received: {str(e)}")
        raise BadRequest(f"Invalid JSON: {str(e)}")
    
    try:
        event = IncomingEvent(**raw_data)
    except Exception as e:
        logger.warning(f"Validation failed: {str(e)}")
        raise BadRequest(f"Invalid event data: {str(e)}")
    
    # Логируем с correlation_id
    logger.info(
        f"Event received: id={event.event_id}, "
        f"type={event.event_type}, source={event.source}, "
        f"correlation_id={correlation_id}",
        extra={'event_id': event.event_id, 'correlation_id': correlation_id}
    )
    
    # Сериализуем событие в JSON
    message_body = event.serialize_to_json()
    
    # Отправляем в RabbitMQ с correlation_id в заголовках
    try:
        rabbit_producer.publish(
            queue_name=Config.RABBIT_QUEUE_EVENTS,
            message_body=message_body,
            headers={
                'event_id': event.event_id,
                'event_type': event.event_type,
                'source': event.source,
                'schema_version': str(event.schema_version),
                'correlation_id': correlation_id  # Добавляем correlation_id
            }
        )
        logger.info(f"Event {event.event_id} published to RabbitMQ, correlation: {correlation_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish event to RabbitMQ: {e}, correlation: {correlation_id}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to process event"
        }), 500
    
    return jsonify({
        "event_id": event.event_id,
        "correlation_id": correlation_id,  # Добавляем в ответ
        "status": "accepted",
        "message": "Event published to queue"
    }), 202


@app.errorhandler(BadRequest)
def handle_bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error.description)
    }), 400


@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(error):
    return jsonify({
        "error": "Request Entity Too Large",
        "message": str(error.description)
    }), 413


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.error(f"Unexpected error: {str(error)}", exc_info=True)
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }), 500


@app.teardown_appcontext
def teardown_rabbit(exception=None):
    """Закрываем соединение с RabbitMQ при завершении приложения"""
    rabbit_producer.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
