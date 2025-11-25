import logging
import os
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

API_URL = os.getenv("API_URL", "http://localhost:8000")
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
/current - текущая погода
/help - справка

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    if not update.message:
        return

    help_text = """
📖 *Справка по командам*

/start - начать работу с ботом
/current - текущие показания температуры и влажности
/help - эта справка

_Бот показывает данные с метеостанции в реальном времени_
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
    application.add_handler(CommandHandler("help", help_command))

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
