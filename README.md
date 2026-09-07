# METAR Bot ✈️

A Telegram bot that fetches current METAR aviation weather reports by ICAO airport code and decodes them into plain language. Send it `LTAI` and it replies with the raw METAR plus a human-friendly breakdown of wind, visibility, clouds, weather phenomena, temperature/dew point/humidity, QNH and trend. The decoded output is in Turkish.

## Features

- **METAR decoding** — wind, visibility, clouds, weather phenomena, temperature/dew point, relative humidity, QNH and `TEMPO`/`BECMG` trends
- **Runway info** — the `/chart` command shows runway lengths, ILS availability and CAT categories
- **Chart links** — inline buttons for Approach / SID / STAR / Airport Diagram charts via [ChartFox](https://chartfox.org)
- **~80 airports** — mostly Turkish airports (LTFM, LTBA, LTAI...) plus major international hubs (KJFK, EGLL, OMDB...)
- **PaaS-ready** — health-check endpoints (`/` and `/health`) for keep-alive on platforms like Render or Railway

## Commands

| Command | Description |
|---|---|
| `LTAI` (just a message) | Fetches the current METAR report |
| `/start` | Welcome message with usage examples |
| `/chart LTAI` | Runway info and chart links (inline button menu) |

## Setup

```bash
git clone https://github.com/yuefsaedu/metar-bot.git
cd metar-bot
pip install -r requirements.txt
```

Create a `.env` file with the token from [@BotFather](https://t.me/BotFather):

```
BOT_TOKEN=123456:ABC-DEF...
```

Run:

```bash
gunicorn -c gunicorn.conf.py app:app
```

The bot runs as a background thread alongside the Flask server.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram bot token (@BotFather) |
| `PORT` | ❌ | Flask/gunicorn port (default: `10000`) |

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yuefsaedu/metar-bot)

`render.yaml` is included; all you need to do is set the `BOT_TOKEN` env var.

## Data Source

METAR data is fetched in real time from the [AviationWeather.gov](https://aviationweather.gov) API.

## License

[MIT](LICENSE)
