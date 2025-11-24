import json
import os
import sys
import time

import dotenv
import serial

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import SessionLocal
from shared.models import WeatherData


dotenv.load_dotenv()


def read_arduino_data():
    port = os.getenv("ARDUINO_PORT")
    print(f"Подключение к порту: {port}")

    try:
        ser = serial.Serial(port, 9600, timeout=2)
        print(f"Порт открыт: {ser}")

        # Даем Arduino время на инициализацию
        time.sleep(2)

        # Очищаем буфер на случай старых данных
        ser.reset_input_buffer()

        print("Ожидание данных от ардуино...")

        # Читаем несколько раз, чтобы поймать данные
        for attempt in range(5):
            bytes_waiting = ser.in_waiting
            print(f"Попытка {attempt + 1}: Байтов в буфере: {bytes_waiting}")

            if bytes_waiting > 0:
                try:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    print(f"Получены необработанные данные: '{line}'")

                    if line:
                        # Пробуем разные варианты парсинга
                        try:
                            data = json.loads(line)
                            print(f"JSON успешно проанализирован: {data}")
                            return data
                        except json.JSONDecodeError as e:
                            print(f"Ошибка декодирования JSON: {e}")
                            print(f"Строка которую не удалось преобразовать: '{line}'")

                            # Пробуем ручной парсинг для отладки
                            if "temperature" in line and "humidity" in line:
                                print(
                                    "В тексте обнаружены температура/влажность, но недопустимый JSON."
                                )
                                # Попробуем извлечь числа из текста
                                import re

                                temp_match = re.search(
                                    r"temperature[^0-9]*([0-9.]+)", line
                                )
                                humid_match = re.search(
                                    r"humidity[^0-9]*([0-9.]+)", line
                                )
                                if temp_match and humid_match:
                                    temp = float(temp_match.group(1))
                                    humid = float(humid_match.group(1))
                                    return {"temperature": temp, "humidity": humid}
                except Exception as e:
                    print(f"Ошибка чтения строки: {e}")

            time.sleep(1)  # Ждем между попытками

        print("После 5 попыток не получено достоверных данных.")
        return None

    except serial.SerialException as e:
        print(f"Ошибка порта: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None


def save_to_database(temperature: float, humidity: float):
    db = SessionLocal()
    try:
        record = WeatherData(temperature=temperature, humidity=humidity)
        db.add(record)
        db.commit()
        print(f"Сохранено в бд: {temperature}°C, {humidity}%")
    except Exception as e:
        print(f"Ошибка бд: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    print("Запуск сборщика данных...")

    # Сначала тестируем подключение
    test_data = read_arduino_data()

    if test_data:
        print("Первоначальное подключение выполнено успешно!")
        if "temperature" in test_data and "humidity" in test_data:
            save_to_database(test_data["temperature"], test_data["humidity"])
    else:
        print("Данные не получены. Проверьте подключение Arduino и скетч.")
        print(
            "Убедитесь, что Arduino использует правильный скетч, который отправляет данные JSON."
        )

    # Основной цикл
    print("Запуск основного цикла сбора...")
    while True:
        data = read_arduino_data()
        if data and "temperature" in data and "humidity" in data:
            save_to_database(data["temperature"], data["humidity"])
        else:
            print("Нет валидных данных, ждем...")

        time.sleep(30)  # Ждем 30 секунд между чтениями


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСборщик остановлен пользователем")
