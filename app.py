import os
import re
import logging
import threading
import asyncio
from datetime import datetime, timezone
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

WIND_DIR_TR = {
    'N': 'Kuzey', 'NNE': 'Kuzey Kuzeydogu', 'NE': 'Kuzeydogu', 'ENE': 'Dogu Kuzeydogu',
    'E': 'Dogu', 'ESE': 'Dogu Guneydogu', 'SE': 'Guneydogu', 'SSE': 'Guney Guneydogu',
    'S': 'Guney', 'SSW': 'Guney Guneybati', 'SW': 'Guneybati', 'WSW': 'Bati Guneybati',
    'W': 'Bati', 'WNW': 'Bati Kuzeybati', 'NW': 'Kuzeybati', 'NNW': 'Kuzey Kuzeybati',
}

WEATHER_CODES = {
    'BR': 'Pus', 'DU': 'Genis capli toz', 'DZ': 'Cigenti', 'DS': 'Toz firtinasi',
    'FC': 'Hortum', 'FG': 'Sis', 'FU': 'Duman', 'GR': 'Dolu', 'GS': 'Kucuk dolu',
    'HZ': 'Pusluk', 'IC': 'Buz kristalleri', 'PL': 'Buz pelletleri', 'PO': 'Toz hortumlari',
    'PY': 'Sise', 'RA': 'Yagmur', 'SA': 'Kum', 'SG': 'Kar taneleri', 'SN': 'Kar',
    'SQ': 'Sikistir', 'SS': 'Kum firtinasi', 'TS': 'Gokgurultlu firtina', 'UP': 'Bilinmeyen',
    'VA': 'Volkanik kul', 'TSRA': 'Gokgurultlu yagmur', 'TSGR': 'Gokgurultlu dolu',
    'TSGS': 'Gokgurultlu kucuk dolu', 'FZRA': 'Donan yagmur', 'FZDZ': 'Donan cigenti',
    'SHRA': 'Saganak yagmur', 'SHSN': 'Saganak kar', 'SHGR': 'Saganak dolu',
    'SHGS': 'Saganak kucuk dolu', 'SHPE': 'Saganak buz pelletleri',
    'BCFG': 'Yamali sis', 'BLDU': 'Ucan toz', 'BLSA': 'Ucan kum', 'BLSN': 'Ucan kar',
    'DRDU': 'Suruklenen toz', 'DRSA': 'Suruklenen kum', 'DRSN': 'Suruklenen kar',
    'MIFG': 'Sigin sis', 'PRFG': 'Kismi sis', 'VCTS': 'Yakin gokgurultlu firtina',
    'VCSH': 'Yakin saganak',
}

CLOUD_TYPES = {
    'FEW': 'Seyrek', 'SCT': 'Parcali', 'BKN': 'Kirik', 'OVC': 'Kapali',
    'SKC': 'Açik gökyüzü', 'CLR': 'Açik gökyüzü', 'NSC': 'Onemsiz bulut',
}

INTENSITY_PREFIX = {'-': 'Hafif', '+': 'Kuvvetli', 'VC': 'Yakin'}


def wind_direction_label(deg: str) -> str:
    if deg == 'VRB':
        return 'Degisen'
    try:
        d = int(deg)
        dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        idx = round(d / 22.5) % 16
        return WIND_DIR_TR.get(dirs[idx], dirs[idx])
    except ValueError:
        return deg


def parse_metar(raw: str) -> str:
    parts = raw.strip().split()
    lines = []
    i = 0

    icao = parts[i]; i += 1
    lines.append(f"__Havalimani:__ *{icao}*")

    if i < len(parts):
        time_str = parts[i]; i += 1
        try:
            day = int(time_str[:2])
            hour = int(time_str[2:4])
            minute = int(time_str[4:6])
            indicator = time_str[6] if len(time_str) > 6 else 'Z'
            now = datetime.now(timezone.utc)
            month = now.month
            year = now.year
            if day > now.day + 1:
                if month == 1:
                    month = 12; year -= 1
                else:
                    month -= 1
            auto = " _(Otomatik)_" if indicator == 'A' else ""
            lines.append(f"__Gozlem Zamani:__ {day:02d}/{month:02d}/{year} {hour:02d}:{minute:02d} UTC{auto}")
        except (ValueError, IndexError):
            lines.append(f"__Gozlem Zamani:__ {time_str}")

    if i < len(parts) and parts[i] == 'AUTO':
        lines.append("__Turu:__ Otomatik istasyon")
        i += 1

    if i < len(parts) and parts[i] == 'COR':
        lines.append("__Turu:__ Duzeltilmis rapor")
        i += 1

    if i < len(parts):
        wind = parts[i]; i += 1
        if wind == '00000KT':
            lines.append("__Ruzgar:__ Ruzgarsiz")
        elif 'VRB' in wind:
            m = re.match(r'VRB(\d+)G?(\d+)?(KT|MPS|KMH)', wind)
            if m:
                gust = f"G{m.group(2)}" if m.group(2) else ""
                unit = 'kt' if m.group(3) == 'KT' else 'm/s' if m.group(3) == 'MPS' else 'km/s'
                lines.append(f"__Ruzgar:__ Degisen yon, {m.group(1)}{gust} {unit}")
        else:
            m = re.match(r'(\d{3})(\d{2,3})G?(\d+)?(KT|MPS|KMH)', wind)
            if m:
                direction = m.group(1)
                speed = m.group(2)
                gust = m.group(3)
                unit = 'kt' if m.group(4) == 'KT' else 'm/s' if m.group(4) == 'MPS' else 'km/s'
                dir_label = wind_direction_label(direction)
                gust_str = f", hamle {gust} {unit}" if gust else ""
                lines.append(f"__Ruzgar:__ {dir_label} ({direction}°) {speed} {unit}{gust_str}")

    if i < len(parts):
        vis = parts[i]; i += 1
        if vis.isdigit() or (vis.startswith('-') and vis[1:].isdigit()):
            vis_val = int(vis.replace('-', ''))
            if vis_val >= 9999:
                lines.append(f"__Gorunurluk:__ 10+ km")
            else:
                lines.append(f"__Gorunurluk:__ {vis_val} m")
        elif 'SM' in vis:
            lines.append(f"__Gorunurluk:__ {vis}")
        elif '/' in vis and 'SM' in parts[i] if i < len(parts) else False:
            lines.append(f"__Gorunurluk:__ {vis} {parts[i]}")
            i += 1

    weather_items = []
    while i < len(parts):
        p = parts[i]
        if re.match(r'^[+-]?(VC)?(?:BR|DU|DZ|DS|FC|FG|FU|GR|GS|HZ|IC|PL|PO|PY|RA|SA|SG|SN|SQ|SS|TS|UP|VA|TSRA|TSGR|TSGS|FZRA|FZDZ|SHRA|SHSN|SHGR|SHGS|BLDU|BLSA|BLSN|DRDU|DRSA|DRSN|BCFG|MIFG|PRFG|SHPE)$', p):
            prefix = ''
            weather = p
            if p[0] in '+-':
                prefix = INTENSITY_PREFIX.get(p[0], '')
                weather = p[1:]
            elif p.startswith('VC'):
                prefix = INTENSITY_PREFIX.get('VC', '')
                weather = p[2:]

            label = WEATHER_CODES.get(weather, weather)
            if prefix:
                label = f"{prefix} {label}"
            weather_items.append(label)
            i += 1
        else:
            break

    if weather_items:
        lines.append(f"__Hava Durumu:__ {', '.join(weather_items)}")

    cloud_lines = []
    while i < len(parts):
        p = parts[i]
        m = re.match(r'^(FEW|SCT|BKN|OVC|SKC|CLR|NSC|VV)(\d{3})(?:CB|TCU)?$', p)
        if m:
            ctype = m.group(1)
            height = int(m.group(2)) * 100
            feet = f"{height:,} ft"
            m_to = f" (~{int(height * 0.3048):,} m)"
            type_tr = CLOUD_TYPES.get(ctype, ctype)
            if ctype == 'VV':
                cloud_lines.append(f"Dikey gorus mesafesi: {feet}{m_to}")
            else:
                extra = ""
                if p.endswith('CB'):
                    extra = " (Cb)"
                elif p.endswith('TCU'):
                    extra = " (TCU)"
                cloud_lines.append(f"{type_tr} {feet}{m_to}{extra}")
            i += 1
        else:
            break

    if cloud_lines:
        lines.append(f"__Bulutlar:__ {', '.join(cloud_lines)}")

    if i < len(parts):
        temp_part = parts[i]; i += 1
        m = re.match(r'(M?\d{2})/(M?\d{2})', temp_part)
        if m:
            temp = int(m.group(1).replace('M', '-'))
            dew = int(m.group(2).replace('M', '-'))
            temp_s = f"{temp}°C" if temp >= 0 else f"-{abs(temp)}°C"
            dew_s = f"{dew}°C" if dew >= 0 else f"-{abs(dew)}°C"
            lines.append(f"__Sicaklik:__ {temp_s}  |  __Cig Noktasi:__ {dew_s}")

    if i < len(parts):
        qnh_part = parts[i]; i += 1
        m = re.match(r'Q(\d{4})', qnh_part)
        if m:
            qnh = int(m.group(1))
            inhg = qnh * 0.02953
            lines.append(f"__QNH:__ {qnh} hPa ({inhg:.2f} inHg)")

    if i < len(parts):
        rewx = parts[i]
        if rewx.startswith('RE'):
            i += 1

    while i < len(parts):
        p = parts[i]
        if p == 'NOSIG':
            lines.append("__Onemli Degisiklik:__ Beklenmiyor (NOSIG)")
            i += 1
        elif p == 'TEMPO' or p == 'BECMG' or p == 'FM' or p == 'PROB':
            trend_parts = [p]
            i += 1
            while i < len(parts) and not parts[i].startswith('RMK') and parts[i] not in ('TEMPO', 'BECMG', 'FM', 'PROB'):
                trend_parts.append(parts[i])
                i += 1
            trend_label = {'TEMPO': 'Gecici', 'BECMG': 'Donusen', 'FM': 'Buradan', 'PROB': 'Olasilik'}.get(trend_parts[0], trend_parts[0])
            lines.append(f"__Trend ({trend_label}):__ {' '.join(trend_parts[1:])}")
        elif p == 'RMK':
            remarks = ' '.join(parts[i+1:])
            if remarks.strip():
                lines.append(f"__Notlar:__ {remarks.strip()}")
            break
        elif re.match(r'^R\d{2}[LRC]?/\d{4}[V]?\d*$', p):
            i += 1
        else:
            i += 1

    return '\n'.join(lines)


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
        "\u2708\ufe0f METAR Bot'a hosgeldiniz!\n\n"
        "Havalimani ICAO kodunu gonderin (orn: LTAI), guncel METAR bilgisini ileteyim.\n\n"
        "Ornekler:\n"
        "\u2022 LTAI - Antalya\n"
        "\u2022 LTBA - Istanbul\n"
        "\u2022 LTJF - Ankara"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if not ICAO_PATTERN.match(text):
        await update.message.reply_text(
            "\u26a0\ufe0f Gecersiz ICAO kodu.\n"
            "Lutfen 4 harfli bir ICAO kodu gonderin (orn: LTAI, LTBA)."
        )
        return

    await update.message.chat.send_action("typing")

    result = fetch_metar(text)
    if result and result.get("data"):
        metar_data = result["data"]
        airport = result.get("airportIcao", text)
        decoded = parse_metar(metar_data)
        message = (
            f"\U0001f4e1 *{airport} METAR Raporu*\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"*RAW:*\n`{metar_data}`\n\n"
            "\U0001f4cb *Detayli Rapor:*\n"
            f"{decoded}"
        )
        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"\u274c {text} icin METAR bilgisi alinamadi.\n"
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
    bot_app.run_polling(drop_pending_updates=True, stop_signals=[])


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
