FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y

# Копирование зависимостей
COPY requirements.txt .
COPY shared/ ./shared/
COPY bot/ ./bot/

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Запуск бота
CMD ["python", "bot/main.py"]