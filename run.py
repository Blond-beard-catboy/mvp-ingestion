#!/usr/bin/env python3
# Просто импортируем и запускаем
from api.app import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)