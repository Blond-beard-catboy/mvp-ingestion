#!/bin/bash
cd "$(dirname "$0")/.."

SERVICE=${1:-""}

case "$SERVICE" in
    api|worker|rabbitmq|postgres|mysql|"")
        echo "Просмотр логов сервиса: ${SERVICE:-всех}"
        docker-compose logs -f $SERVICE
        ;;
    *)
        echo "Неизвестный сервис: $SERVICE"
        echo "Доступные сервисы: api, worker, rabbitmq, postgres, mysql"
        echo "Использование: $0 [сервис]"
        exit 1
        ;;
esac