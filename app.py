import os
import re
import logging
import threading
import asyncio
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

app = Flask(__name__)

_bot_started = False


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
    asyncio.set_event_loop(asyncio.new_event_loop())
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("METAR Bot calisiyor...")
    bot_app.run_polling(drop_pending_updates=True)


def start_bot_thread():
    global _bot_started
    if _bot_started:
        return
    _bot_started = True
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()


@app.route("/")
def health():
    return jsonify({"status": "ok", "bot": "metar-bot"})


@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})


start_bot_thread()
