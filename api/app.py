import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from shared.models import IncomingEvent
from shared.logging import setup_logging
from shared.rabbit import RabbitMQProducer
from api.config import Config

app = Flask(__name__)
app.config.from_object(Config)
logger = setup_logging(__name__, Config.LOG_LEVEL)

# Инициализация RabbitMQ продюсера
rabbit_producer = RabbitMQProducer(Config.RABBIT_URL)


@app.before_request
def validate_content_length():
    """Проверка размера тела запроса"""
    if request.content_length and request.content_length > Config.MAX_BODY_BYTES:
        raise RequestEntityTooLarge(
            f"Request body too large. Max size is {Config.MAX_BODY_BYTES} bytes"
        )


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
    
    logger.info(
        f"Event received: id={event.event_id}, "
        f"type={event.event_type}, source={event.source}"
    )
    
    # Сериализуем событие в JSON
    message_body = event.serialize_to_json()
    
    # Отправляем в RabbitMQ
    try:
        rabbit_producer.publish(
            queue_name=Config.RABBIT_QUEUE_EVENTS,
            message_body=message_body,
            headers={
                'event_id': event.event_id,
                'event_type': event.event_type,
                'source': event.source,
                'schema_version': str(event.schema_version)
            }
        )
        logger.info(f"Event {event.event_id} published to RabbitMQ")
        
    except Exception as e:
        logger.error(f"Failed to publish event to RabbitMQ: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "Failed to process event"
        }), 500
    
    return jsonify({
        "event_id": event.event_id,
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