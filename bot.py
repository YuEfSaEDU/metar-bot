import os
import re
import logging
import threading
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = "https://planner.flightsimulator.com/api/v1/weather/metar/"
API_COOKIE = os.getenv(
    "API_COOKIE",
    "ApiToken=wcXZWnXviydjpu9z8GBf7w%3D%3D.9wydkP%2FTKZiGh7FmoQzWy8nYvlSevxXwY%2FQAs5LDcPUBbjy1euVZ%2FzJ9R5QbXE8T0AanA5i4yZZ2krQdAhLiIH6dPA%3D%3D",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ICAO_PATTERN = re.compile(r'^[A-Z]{4}$')

flask_app = Flask(__name__)


def fetch_metar(icao: str) -> dict | None:
    headers = {'Cookie': API_COOKIE}
    try:
        resp = requests.get(f"{API_BASE_URL}{icao}", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"API error for {icao}: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "METAR Bot'a hosgeldiniz!\n\n"
        "Havalimani ICAO kodunu gonderin (orn: LTAI), guncel METAR bilgisini ileteyim.\n\n"
        "Ornekler:\n"
        "- LTAI - Antalya\n"
        "- LTBA - Istanbul\n"
        "- LTJF - Ankara"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if not ICAO_PATTERN.match(text):
        await update.message.reply_text(
            "Gecersiz ICAO kodu.\n"
            "Lutfen 4 harfli bir ICAO kodu gonderin (orn: LTAI, LTBA)."
        )
        return

    await update.message.chat.send_action("typing")

    result = fetch_metar(text)
    if result and result.get("data"):
        metar_data = result["data"]
        airport = result.get("airportIcao", text)
        await update.message.reply_text(
            f"{airport} METAR\n\n"
            f"{metar_data}"
        )
    else:
        await update.message.reply_text(
            f"{text} icin METAR bilgisi alinamadi.\n"
            "ICAO kodunu kontrol edip tekrar deneyin."
        )


def run_bot():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN bulunamadi!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("METAR Bot calisiyor...")
    app.run_polling(drop_pending_updates=True)


@flask_app.route("/")
def health():
    return jsonify({"status": "ok", "bot": "metar-bot"})


@flask_app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})


def main():
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
