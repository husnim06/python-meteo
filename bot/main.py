import os

import dotenv
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


dotenv.load_dotenv()

API_URL = "http://localhost:8000"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    await update.message.reply_text(
        "🌤️ Бот метеостанции\nКоманда:\n/current - текущая погода"
    )


async def current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    try:
        response = requests.get(f"{API_URL}/api/current")
        if response.status_code == 200:
            data = response.json()
            message = (
                f"🌡 Температура: {data['temperature']:.1f}°C\n"
                f"💧 Влажность: {data['humidity']:.1f}%"
            )
        else:
            message = "❌ Нет актуальных данных"
    except requests.RequestException:
        message = "❌ Не удалось подключиться к метеостанции"

    await update.message.reply_text(message)


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN переменная среды отсутствует")
        return
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("current", current))

    print("Бот работает...")
    application.run_polling()


if __name__ == "__main__":
    main()
