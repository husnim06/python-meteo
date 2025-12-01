import base64
import logging
import os
from io import BytesIO
from typing import Dict, Optional

import dotenv
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

dotenv.load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

API_HOST = os.getenv("API_HOST")
API_PORT = os.getenv("API_PORT")
API_URL = f"http://{API_HOST}:{API_PORT}"
BOT_TOKEN = os.getenv("BOT_TOKEN")


def fetch_weather_data() -> Optional[Dict]:
    """Асинхронное получение данных о погоде из API"""
    try:
        response = requests.get(f"{API_URL}/api/current")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Получены данные от API: {data}")
            return data
        else:
            logger.warning(f"API вернул статус {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not update.message:
        return

    welcome_text = """
🌤️ *Бот метеостанции*

Доступные команды:
/start - начать работу с ботом
/current - текущие показания температуры и влажности
/stats [часы] - статистика за период (по умолчанию 24 часа)
/chart [часы] [temp/hum] - график температуры/влажности
/help - эта справка

_Для получения актуальных данных о температуре и влажности_
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /current"""
    if not update.message:
        return

    # Показываем индикатор "печатает"
    await update.message.chat.send_action(action="typing")

    data = fetch_weather_data()

    if data and "temperature" in data and "humidity" in data:
        # Форматируем красивое сообщение
        temp = data["temperature"]
        humidity = data["humidity"]
        timestamp = data.get("timestamp", "")

        # Определяем эмодзи для температуры
        if temp < 0:
            temp_emoji = "❄️"
        elif temp < 15:
            temp_emoji = "☁️"
        elif temp < 25:
            temp_emoji = "🌤️"
        else:
            temp_emoji = "🔥"

        # Определяем эмодзи для влажности
        if humidity < 30:
            humid_emoji = "🏜️"
        elif humidity < 60:
            humid_emoji = "💧"
        else:
            humid_emoji = "🌧️"

        message = (
            f"{temp_emoji} *Температура:* {temp:.1f}°C\n"
            f"{humid_emoji} *Влажность:* {humidity:.1f}%\n"
        )

        if timestamp:
            message += f"\n_Обновлено: {timestamp}_"

    else:
        message = (
            "❌ *Не удалось получить данные*\n\n"
            "Метеостанция временно недоступна. "
            "Попробуйте позже."
        )

    await update.message.reply_text(message, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику за период"""
    if not update.message:
        return

    await update.message.chat.send_action(action="typing")

    # Получаем период из аргументов (по умолчанию 24 часа)
    hours = 24
    if context.args and context.args[0].isdigit():
        hours = min(int(context.args[0]), 168)  # Максимум неделя

    try:
        response = requests.get(f"{API_URL}/api/history?hours={hours}")
        if response.status_code == 200:
            data = response.json()

            stats = data["stats"]
            message = (
                f"📊 *Статистика за последние {hours} часов*\n\n"
                f"🌡️ *Температура:*\n"
                f"   Средняя: {stats['avg_temperature']:.1f}°C\n"
                f"   Макс: {stats['max_temperature']:.1f}°C\n"
                f"   Мин: {stats['min_temperature']:.1f}°C\n\n"
                f"💧 *Влажность:*\n"
                f"   Средняя: {stats['avg_humidity']:.1f}%\n"
                f"   Макс: {stats['max_humidity']:.1f}%\n"
                f"   Мин: {stats['min_humidity']:.1f}%\n\n"
                f"📈 *Всего записей:* {stats['records_count']}"
            )
        else:
            message = "❌ Не удалось получить статистику"

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        message = "🔧 Ошибка при получении статистики"

    await update.message.reply_text(message, parse_mode="Markdown")


async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить график погоды"""
    if not update.message:
        return

    await update.message.chat.send_action(action="upload_photo")

    # Парсим аргументы с улучшенной логикой
    hours = 24
    chart_type = "both"

    if context.args:
        for arg in context.args:
            arg_lower = arg.lower()
            if arg_lower.isdigit():
                hours = min(int(arg_lower), 168)  # Максимум неделя
            elif arg_lower in ["temp", "temperature", "t"]:
                chart_type = "temperature"
            elif arg_lower in ["hum", "humidity", "h"]:
                chart_type = "humidity"
            elif arg_lower == "both":
                chart_type = "both"

    try:
        response = requests.get(
            f"{API_URL}/api/chart?hours={hours}&chart_type={chart_type}"
        )

        if response.status_code == 200:
            chart_data = response.json()
            image_data = chart_data["image"].split(",")[
                1
            ]  # Убираем data:image/png;base64,
            image_bytes = base64.b64decode(image_data)

            # Создаем подпись с информацией
            type_names = {
                "temperature": "температуры",
                "humidity": "влажности",
                "both": "температуры и влажности",
            }

            caption = (
                f"📈 График {type_names[chart_type]}\n"
                f"🕐 Период: последние {hours} часов\n"
                f"📊 Точек данных: {hours * 2}"  # Примерно, т.к. данные каждые 30 мин
            )

            # Отправляем изображение
            await update.message.reply_photo(
                photo=BytesIO(image_bytes), caption=caption
            )

        elif response.status_code == 404:
            await update.message.reply_text(
                "❌ Нет данных для построения графика за указанный период"
            )
        elif response.status_code == 400:
            await update.message.reply_text(
                "❌ Недостаточно данных для построения графика\n"
                "Попробуйте увеличить период"
            )
        else:
            await update.message.reply_text("❌ Ошибка при генерации графика")
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        await update.message.reply_text("🔧 Техническая ошибка при создании графика")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    if not update.message:
        return

    help_text = """
📖 *Справка по командам*

/start - начать работу с ботом
/current - текущие показания температуры и влажности
/stats [часы] - статистика за период (по умолчанию 24 часа)
/chart [часы] [temp/hum] - график температуры/влажности
/help - эта справка

*Примеры:*
/stats 48 - статистика за 48 часов
/chart 12 temp - график температуры за 12 часов
/chart 72 - общий график за 72 часа
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("current", current))
    application.add_handler(CommandHandler("stats", stats))  # Новая команда
    application.add_handler(CommandHandler("chart", chart))  # Новая команда
    application.add_handler(CommandHandler("help", help_command))

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
