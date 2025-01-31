#!/bin/bash

# Путь к директории приложения
APP_DIR="/root/tachka"

# Проверка существования директории
if [[ ! -d "$APP_DIR" ]]; then
  echo "Ошибка: Директория $APP_DIR не найдена!"
  exit 1
fi

# Переход в директорию
cd "$APP_DIR" || exit

# Путь к сертификатам
CERTFILE="/etc/letsencrypt/live/szhnserv.ru/fullchain.pem"
KEYFILE="/etc/letsencrypt/live/szhnserv.ru/privkey.pem"

# Проверка наличия сертификатов
if [[ ! -f "$CERTFILE" || ! -f "$KEYFILE" ]]; then
  echo "Ошибка: Сертификаты не найдены!"
  echo "Убедитесь, что файлы $CERTFILE и $KEYFILE существуют."
  exit 1
fi

# Запуск Gunicorn с UvicornWorker
gunicorn -k uvicorn.workers.UvicornWorker main:app \
 --bind=0.0.0.0:443 \
 --workers 6 \
 --certfile="$CERTFILE" \
 --keyfile="$KEYFILE" \