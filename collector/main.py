import json
import logging
import os
import sys
import time
from typing import Dict, Optional

import dotenv
import serial

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import SessionLocal, create_tables
from shared.models import WeatherData

dotenv.load_dotenv()

logger = logging.getLogger("data_collector")


class ArduinoReader:
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def __enter__(self):
        """Контекстный менеджер для безопасной работы с портом"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(4)  # Ожидание инициализации Arduino
            self.ser.reset_input_buffer()
            logger.info(f"Успешное подключение к порту {self.port}")
            return self
        except serial.SerialException as e:
            logger.error(f"Ошибка подключения к {self.port}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Гарантированное закрытие порта"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial порт закрыт")

    def read_single_reading(self) -> Optional[Dict]:
        """Читает одно показание с Arduino"""
        if not self.ser or not self.ser.is_open:
            return None

        for attempt in range(5):
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode("utf-8", errors="ignore").strip()

                    if not line:
                        continue

                    data = self.safe_json_parse(line)
                    if data:
                        return data

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Попытка {attempt+1}: Ошибка парсинга - {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка при чтении: {e}")

            time.sleep(1)

        logger.error("Не удалось получить валидные данные после 5 попыток")
        return None

    def safe_json_parse(self, line: str) -> Optional[Dict]:
        """Безопасный парсинг JSON с валидацией"""
        try:
            # Очистка строки
            line = "".join(char for char in line if char.isprintable()).strip()
            if not line:
                return None

            data = json.loads(line)

            # Валидация структуры и значений
            if not all(key in data for key in ["temperature", "humidity"]):
                return None

            if not isinstance(data["temperature"], (int, float)) or not isinstance(
                data["humidity"], (int, float)
            ):
                return None

            # Валидация физических пределов
            if not (-50 <= data["temperature"] <= 60 and 0 <= data["humidity"] <= 100):
                logger.warning(f"Некорректные значения: {data}")
                return None

            return data

        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            return None


def save_weather_data(temperature: float, humidity: float):
    """Сохраняет данные в базу с обработкой ошибок"""
    db = SessionLocal()
    try:
        record = WeatherData(temperature=temperature, humidity=humidity)
        db.add(record)
        db.commit()
        logger.info(f"Сохранено: {temperature}°C, {humidity}%")
    except Exception as e:
        logger.error(f"Ошибка сохранения в БД: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Основная функция сбора данных"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Создаем таблицы при первом запуске
    create_tables()

    port = os.getenv("ARDUINO_PORT")
    if not port:
        logger.error("ARDUINO_PORT не указан в .env")
        return

    logger.info("Запуск сборщика метеоданных...")

    try:
        with ArduinoReader(port) as reader:
            # Тестовое чтение
            test_data = reader.read_single_reading()
            if test_data:
                logger.info("Тестовое подключение успешно")
            else:
                logger.warning("Тестовые данные не получены")

            # Основной цикл
            logger.info("Запуск основного цикла сбора (30 сек интервал)")
            while True:
                data = reader.read_single_reading()
                if data:
                    save_weather_data(data["temperature"], data["humidity"])
                else:
                    logger.warning("Нет валидных данных в этом цикле")

                time.sleep(30)

    except KeyboardInterrupt:
        logger.info("Сборщик остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    main()
