# METAR Bot 🛩️

Telegram'a bir ICAO havalimanı kodu yazın (örn. `LTAI`), bot o havalimanının güncel **METAR** hava raporunu hem ham hem de **Türkçe çözümlenmiş** olarak göndersin.

A Telegram bot that fetches current METAR aviation weather reports by ICAO code and decodes them into Turkish (wind, visibility, clouds, weather phenomena, temperature/dew point/humidity, QNH and trend).

## Özellikler

- **Türkçe METAR çözümleme** — rüzgâr, görüş, bulutlar, hava olayları, sıcaklık/nem, QNH ve `TEMPO`/`BECMG` trendleri
- **Pist bilgisi** — `/chart` komutuyla pist uzunlukları, ILS durumu ve CAT kategorileri
- **Graf erişimi** — Approach / SID / STAR / Airport Diagram linkleri ([ChartFox](https://chartfox.org) üzerinden)
- **~80 havalimanı** — Türkiye'deki havalimanları ağırlıklı (LTFM, LTBA, LTAI...) + dünya çapında önemli noktalar (KJFK, EGLL, OMDB...)
- **PaaS uyumlu** — Render/Railway gibi platformlarda çalışmak için health-check endpoint'leri (`/` ve `/health`)

## Komutlar

| Komut | Açıklama |
|---|---|
| `LTAI` (sadece mesaj) | Güncel METAR raporunu getirir |
| `/start` | Karşılama mesajı ve kullanım örnekleri |
| `/chart LTAI` | Pist bilgileri ve graf linkleri (butonlu menü) |

## Kurulum

```bash
git clone https://github.com/yuefsaedu/metar-bot.git
cd metar-bot
pip install -r requirements.txt
```

`.env` dosyası oluşturun ([@BotFather](https://t.me/BotFather)'dan aldığınız token ile):

```
BOT_TOKEN=123456:ABC-DEF...
```

Çalıştırma:

```bash
gunicorn -c gunicorn.conf.py app:app
```

Bot, Flask sunucusuyla birlikte arka planda thread olarak çalışır.

## Ortam Değişkenleri

| Değişken | Zorunlu | Açıklama |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram bot token'ı (@BotFather) |
| `PORT` | ❌ | Flask/gunicorn portu (varsayılan: `10000`) |

## Render'a Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yuefsaedu/metar-bot)

`render.yaml` hazır gelir; tek yapmanız gereken `BOT_TOKEN` env var'ını girmek.

## Veri Kaynağı

METAR verileri [AviationWeather.gov](https://aviationweather.gov) API'sinden gerçek zamanlı olarak alınır.

## Lisans

[MIT](LICENSE)
