# Используем базовый образ Python
FROM python:3.10-slim

# Установка зависимостей
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем весь проект в контейнер
COPY . /app
WORKDIR /app

# Переменная для настройки команды запуска
ENV GUNICORN_CMD=""

# Указываем команду по умолчанию (переопределяется в docker-compose.yml)
CMD ["sh", "-c", "$GUNICORN_CMD"]