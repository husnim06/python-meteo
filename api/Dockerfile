FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y

# Копирование зависимостей
COPY requirements.txt .
COPY shared/ ./shared/
COPY api/ ./api/

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Создание папки для бд
# RUN mkdir -p /app/data

# Открытие порта
EXPOSE 8000

# Запуск бэка
CMD ["python", "api/main.py"]