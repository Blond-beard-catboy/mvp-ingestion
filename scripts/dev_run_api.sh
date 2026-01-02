#!/bin/bash
cd "$(dirname "$0")/.."

if [ -d "venv" ]; then
    source venv/bin/activate
fi

if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Copy .env.example to .env"
fi

echo "Starting Flask API..."
# Просто запускаем app.py напрямую
python api/app.py