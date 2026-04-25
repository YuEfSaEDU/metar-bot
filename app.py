import os
import re
import logging
import threading
import asyncio
from datetime import datetime, timezone
from html import escape
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
METAR_API = "https://aviationweather.gov/api/data/metar"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ICAO_PATTERN = re.compile(r'^[A-Z]{4}$')

AIRPORTS = {
    'LTAI': ('Antalya', 'Antalya Havalimani'),
    'LTBA': ('Istanbul', 'Istanbul Ataturk Havalimani'),
    'LTFM': ('Istanbul', 'Istanbul Havalimani'),
    'LTJF': ('Ankara', 'Ankara Esenboga Havalimani'),
    'LTAC': ('Ankara', 'Ankara Esenboga Havalimani'),
    'LTBJ': ('Izmir', 'Izmir Adnan Menderes Havalimani'),
    'LTBS': ('Dalaman', 'Dalaman Havalimani'),
    'LTAF': ('Izmir', 'Izmir Cigli Havalimani'),
    'LTAL': ('Kars', 'Kars Harakani Havalimani'),
    'LTAM': ('Kayseri', 'Kayseri Erkilet Havalimani'),
    'LTAN': ('Malatya', 'Malatya Erhac Havalimani'),
    'LTAP': ('Gaziantep', 'Gaziantep Oguzeli Havalimani'),
    'LTAQ': ('Erzurum', 'Erzurum Havalimani'),
    'LTAR': ('Van', 'Van Ferit Melen Havalimani'),
    'LTAS': ('Sivas', 'Sivas Nuri Demirag Havalimani'),
    'LTAT': ('Elazig', 'Elazig Havalimani'),
    'LTAU': ('Sanliurfa', 'Sanliurfa GAP Havalimani'),
    'LTAV': ('Adana', 'Adana Sakirpasa Havalimani'),
    'LTAW': ('Samsun', 'Samsun Carsamba Havalimani'),
    'LTAX': ('Mugla', 'Mugla Dalaman Havalimani'),
    'LTAZ': ('Mersin', 'Mersin (Tarsus) Havalimani'),
    'LTB1': ('Bursa', 'Bursa Yenisehir Havalimani'),
    'LTBB': ('Bodrum', 'Bodrum Milas Havalimani'),
    'LTBC': ('Canakkale', 'Canakkale Havalimani'),
    'LTBD': ('Bursa', 'Bursa Havalimani'),
    'LTBE': ('Denizli', 'Denizli Cardak Havalimani'),
    'LTBF': ('Eskisehir', 'Eskisehir Hasan Polatkan Havalimani'),
    'LTBG': ('Tekirdag', 'Tekirdag Corlu Havalimani'),
    'LTBH': ('Balikesir', 'Balikesir Merkez Havalimani'),
    'LTBI': ('Bilecik', 'Bilecik Havalimani'),
    'LTBJ': ('Izmir', 'Izmir Adnan Menderes Havalimani'),
    'LTBK': ('Izmir', 'Izmir Selcuk (Efes) Havalimani'),
    'LTBL': ('Isparta', 'Isparta Suleyman Demirel Havalimani'),
    'LTBM': ('Mardin', 'Mardin Havalimani'),
    'LTBN': ('Kastamonu', 'Kastamonu Havalimani'),
    'LTBO': ('Kutahya', 'Kutahya Zafer Havalimani'),
    'LTBP': ('Sinop', 'Sinop Havalimani'),
    'LTBR': ('Yalova', 'Yalova Havalimani'),
    'LTBY': ('Nevsehir', 'Nevsehir Kapadokya Havalimani'),
    'LTCA': ('Trabzon', 'Trabzon Havalimani'),
    'LTCB': ('Erzincan', 'Erzincan Havalimani'),
    'LTCC': ('Bingol', 'Bingol Havalimani'),
    'LTCD': ('Diyarbakir', 'Diyarbakir Havalimani'),
    'LTCE': ('Mus', 'Mus Havalimani'),
    'LTCF': ('Kahramanmaras', 'Kahramanmaras Havalimani'),
    'LTCG': ('Rize', 'Rize Artvin Havalimani'),
    'LTCH': ('Hakkari', 'Hakkari Yuksekova Havalimani'),
    'LTCI': ('Gumushane', 'Gumushane Havalimani'),
    'LTCN': ('Giresun', 'Giresun Ordu Havalimani'),
    'LTCP': ('Batman', 'Batman Havalimani'),
    'LTCR': ('Igdir', 'Igdir Havalimani'),
    'LTCS': ('Sirnak', 'Sirnak Serafettin Elci Havalimani'),
    'LTCT': ('Sirnak', 'Sirnak Havalimani'),
    'LTCU': ('Agri', 'Agri Ahmed-i Hani Havalimani'),
    'LTCV': ('Tunceli', 'Tunceli Havalimani'),
    'LTCW': ('Ardahan', 'Ardahan Havalimani'),
    'LTDA': ('Hatay', 'Hatay Havalimani'),
    'LTDB': ('Adiyaman', 'Adiyaman Havalimani'),
    'LTDC': ('Kilis', 'Kilis Havalimani'),
    'LTDD': ('Osmaniye', 'Osmaniye Havalimani'),
    'LTDE': ('Yozgat', 'Yozgat Havalimani'),
    'LTDF': ('Kirsehir', 'Kirsehir Havalimani'),
    'LTDH': ('Nigde', 'Nigde Havalimani'),
    'LTFC': ('Istanbul', 'Istanbul Sabiha Gokcen Havalimani'),
    'LTFJ': ('Istanbul', 'Istanbul Sabiha Gokcen Havalimani'),
    'LTFE': ('Izmir', 'Izmir Selcuk Havalimani'),
    'LTAH': ('Konya', 'Konya Havalimani'),
    'LTAG': ('Sivas', 'Sivas Nuri Demirag Havalimani'),
    'LTAD': ('Ankara', 'Ankara Etimesgut Havalimani'),
    'LTNG': ('Ordu-Giresun', 'Ordu-Giresun Havalimani'),
    'LTCF': ('Kahramanmaras', 'Kahramanmaras Havalimani'),
    'LFPG': ('Paris', 'Paris Charles de Gaulle'),
    'EGLL': ('Londra', 'Londra Heathrow'),
    'EDDF': ('Frankfurt', 'Frankfurt Havalimani'),
    'KJFK': ('New York', 'New York JFK'),
    'KLAX': ('Los Angeles', 'Los Angeles Intl'),
    'KBOS': ('Boston', 'Boston Logan Intl'),
    'KORD': ('Chicago', "Chicago O'Hare"),
    'KSFO': ('San Francisco', 'San Francisco Intl'),
    'KATL': ('Atlanta', 'Atlanta Hartsfield-Jackson'),
    'KDFW': ('Dallas', 'Dallas/Fort Worth'),
    'KDEN': ('Denver', 'Denver Intl'),
    'KSEA': ('Seattle', 'Seattle-Tacoma Intl'),
    'KMIA': ('Miami', 'Miami Intl'),
    'KLAS': ('Las Vegas', 'Las Vegas McCarran'),
    'KPHX': ('Phoenix', 'Phoenix Sky Harbor'),
    'KIAH': ('Houston', 'Houston George Bush'),
    'KCLT': ('Charlotte', 'Charlotte Douglas'),
    'KDTW': ('Detroit', 'Detroit Metropolitan'),
    'KMEM': ('Memphis', 'Memphis Intl'),
    'K MSP': ('Minneapolis', 'Minneapolis-St Paul'),
    'EDDB': ('Berlin', 'Berlin Brandenburg'),
    'EDDM': ('Munchen', 'Munchen Havalimani'),
    'EDDH': ('Hamburg', 'Hamburg Havalimani'),
    'EDDF': ('Frankfurt', 'Frankfurt Havalimani'),
    'LEMD': ('Madrid', 'Madrid Barajas'),
    'LIRF': ('Roma', 'Roma Fiumicino'),
    'LIRN': ('Napoli', 'Napoli Havalimani'),
    'LIMC': ('Milano', 'Milano Malpensa'),
    'LIPE': ('Bologna', 'Bologna Havalimani'),
    'LIPZ': ('Venedik', 'Venedik Marco Polo'),
    'LPPT': ('Lizbon', 'Lizbon Humberto Delgado'),
    'EHAM': ('Amsterdam', 'Amsterdam Schiphol'),
    'EBBR': ('Brussel', 'Brussel Havalimani'),
    'LSZH': ('Zurich', 'Zurich Havalimani'),
    'LSGG': ('Cenevre', 'Cenevre Havalimani'),
    'LOWW': ('Viyana', 'Viyana Schwechat'),
    'LOWW': ('Viyana', 'Viyana Havalimani'),
    'EPWA': ('Varsova', 'Varsova Chopin'),
    'LKPR': ('Prag', 'Prag Vaclav Havel'),
    'LHBP': ('Budapeste', 'Budapeste Ferenc'),
    'SKBO': ('Bogota', 'Bogota El Dorado'),
    'SAEZ': ('Buenos Aires', 'Buenos Aires Ezeiza'),
    'SBGL': ('Rio de Janeiro', 'Rio de Janeiro Galeao'),
    'SBGR': ('Sao Paulo', 'Sao Paulo Guarulhos'),
    'YSSY': ('Sidney', 'Sidney Kingsford Smith'),
    'YMML': ('Melbourne', 'Melbourne Tullamarine'),
    'NZAA': ('Auckland', 'Auckland Havalimani'),
    'RJTT': ('Tokyo', 'Tokyo Haneda'),
    'RJBB': ('Osaka', 'Osaka Kansai'),
    'RKSI': ('Seul', 'Seul Incheon'),
    'VHHH': ('Hong Kong', 'Hong Kong Intl'),
    'WSSS': ('Singapur', 'Singapur Changi'),
    'VTBS': ('Bangkok', 'Bangkok Suvarnabhumi'),
    'VIDP': ('Delhi', 'Delhi Indira Gandhi'),
    'VABB': ('Mumbai', 'Mumbai Chhatrapati'),
    'OMDB': ('Dubai', 'Dubai Intl'),
    'OTHH': ('Doha', 'Doha Hamad Intl'),
    'OJAI': ('Amman', 'Amman Queen Alia'),
    'LLBG': ('Tel Aviv', 'Tel Aviv Ben Gurion'),
    'HECA': ('Kahire', 'Kahire Intl'),
    'FACT': ('Cape Town', 'Cape Town Intl'),
    'FAOR': ('Johannesburg', 'Johannesburg OR Tambo'),
    'DNMM': ('Lagos', 'Lagos Murtala Muhammed'),
    'DAAG': ('Cezayir', 'Cezayir Houari Boumediene'),
    'GMMN': ('Marakes', 'Marakes Menara'),
    'DTMB': ('Monastir', 'Monastir Habib Bourguiba'),
    'DAAG': ('Cezayir', 'Cezayir Havalimani'),
    'LTCK': ('Kibris', 'Ercan Havalimani'),
    'LCEN': ('Lefkosa', 'Ercan Havalimani'),
    'LCLK': ('Larnaka', 'Larnaka Havalimani'),
    'LCPH': ('Baf', 'Baf Havalimani'),
    'LGAV': ('Atina', 'Atina Eleftherios Venizelos'),
    'LGIR': ('Girit', 'Girit Havalimani'),
    'LTZP': ('Fethiye', 'Fethiye Havalimani'),
    'LTKA': ('Kastellorizo', 'Kastellorizo Havalimani'),
    'LTDM': ('Konya', 'Konya Havalimani'),
    'LTDT': ('Aydin', 'Aydin Havalimani'),
    'LTDK': ('Usak', 'Usak Havalimani'),
    'LTDR': ('Bolu', 'Bolu Havalimani'),
    'LTDS': ('Bilecik', 'Bilecik Havalimani'),
    'LTDU': ('Corum', 'Corum Havalimani'),
    'LTDV': ('Tokat', 'Tokat Havalimani'),
    'LTDW': ('Amasya', 'Amasya Havalimani'),
    'LUBD': ('Banja Luka', 'Banja Luka Havalimani'),
    'LYBE': ('Belgrad', 'Belgrad Nikola Tesla'),
    'LZKZ': ('Kosova', 'Pristina Havalimani'),
    'LWSK': ('Skopje', 'Skopje Havalimani'),
    'LATI': ('Tirana', 'Tirana Havalimani'),
    'LBSF': ('Sofya', 'Sofya Havalimani'),
    'LBWN': ('Varna', 'Varna Havalimani'),
    'LBBG': ('Burgaz', 'Burgaz Havalimani'),
    'LRBS': ('Bukres', 'Bukres Henri Coanda'),
    'LHSM': ('Saraybosna', 'Saraybosna Havalimani'),
}

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
    'SKC': 'Acik gokyuzu', 'CLR': 'Acik gokyuzu', 'NSC': 'Onemsiz bulut',
}

INTENSITY_PREFIX = {'-': 'Hafif', '+': 'Kuvvetli', 'VC': 'Yakin'}

WEATHER_RE = re.compile(
    r'^[+-]?(?:VC)?(?:BR|DU|DZ|DS|FC|FG|FU|GR|GS|HZ|IC|PL|PO|PY|RA|SA|SG|SN|SQ|SS|TS|UP|VA'
    r'|TSRA|TSGR|TSGS|FZRA|FZDZ|SHRA|SHSN|SHGR|SHGS|BLDU|BLSA|BLSN|DRDU|DRSA|DRSN'
    r'|BCFG|MIFG|PRFG|SHPE)$'
)
CLOUD_RE = re.compile(r'^(FEW|SCT|BKN|OVC|SKC|CLR|NSC|VV)(\d{3})(CB|TCU)?$')
WIND_RE = re.compile(r'(\d{3}|VRB)(\d{2,3})G?(\d+)?(KT|MPS|KMH)')
WIND_VAR_RE = re.compile(r'^(\d{3})V(\d{3})$')
TEMP_RE = re.compile(r'^(M?\d{2})/(M?\d{2})$')
QNH_RE = re.compile(r'^Q(\d{4})$')
RUNWAY_VR_RE = re.compile(r'^R\d{2}[LRC]?/\d{4}[V]?\d*$')


def get_airport_info(icao: str) -> tuple[str, str]:
    info = AIRPORTS.get(icao)
    if info:
        return info
    return (icao, '')


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


def parse_wind(wind_str: str) -> str:
    if wind_str == '00000KT':
        return "<b>Ruzgar:</b> Ruzgarsiz"
    m = WIND_RE.match(wind_str)
    if not m:
        return f"<b>Ruzgar:</b> {escape(wind_str)}"
    direction = m.group(1)
    speed = m.group(2)
    gust = m.group(3)
    unit_raw = m.group(4)
    unit = 'kt' if unit_raw == 'KT' else 'm/s' if unit_raw == 'MPS' else 'km/s'
    gust_str = f", hamle {gust} {unit}" if gust else ""
    if direction == 'VRB':
        return f"<b>Ruzgar:</b> Degisen yon, {speed}{gust_str} {unit}"
    dir_label = wind_direction_label(direction)
    return f"<b>Ruzgar:</b> {dir_label} ({direction}\u00b0) {speed} {unit}{gust_str}"


def parse_cloud(cloud_str: str) -> str | None:
    m = CLOUD_RE.match(cloud_str)
    if not m:
        return None
    ctype = m.group(1)
    height = int(m.group(2)) * 100
    feet = f"{height:,} ft"
    m_to = f" (~{int(height * 0.3048):,} m)"
    type_tr = CLOUD_TYPES.get(ctype, ctype)
    if ctype == 'VV':
        return f"Dikey gorus: {feet}{m_to}"
    extra = ""
    if m.group(3) == 'CB':
        extra = " (Cb)"
    elif m.group(3) == 'TCU':
        extra = " (TCU)"
    return f"{type_tr} {feet}{m_to}{extra}"


def parse_weather(wx_str: str) -> str | None:
    if not WEATHER_RE.match(wx_str):
        return None
    prefix = ''
    weather = wx_str
    if wx_str[0] in '+-':
        prefix = INTENSITY_PREFIX.get(wx_str[0], '')
        weather = wx_str[1:]
    elif wx_str.startswith('VC'):
        prefix = INTENSITY_PREFIX.get('VC', '')
        weather = wx_str[2:]
    label = WEATHER_CODES.get(weather, weather)
    if prefix:
        label = f"{prefix} {label}"
    return label


def parse_metar(raw: str, api_name: str = "") -> str:
    parts = raw.strip().split()
    if parts and parts[0] in ('METAR', 'SPECI'):
        parts = parts[1:]
    lines = []
    i = 0

    icao = parts[i]; i += 1
    city, airport_name = get_airport_info(icao)
    if api_name:
        display_name = api_name
    elif airport_name:
        display_name = f"{airport_name}, {city}"
    else:
        display_name = city
    lines.append(f"<b>Havalimani:</b> <code>{icao}</code> - {escape(display_name)}")

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
            auto = " (Otomatik)" if indicator == 'A' else ""
            lines.append(f"<b>Gozlem Zamani:</b> {day:02d}/{month:02d}/{year} {hour:02d}:{minute:02d} UTC{auto}")
        except (ValueError, IndexError):
            lines.append(f"<b>Gozlem Zamani:</b> {escape(time_str)}")

    if i < len(parts) and parts[i] == 'AUTO':
        lines.append("<b>Turu:</b> Otomatik istasyon")
        i += 1

    if i < len(parts) and parts[i] == 'COR':
        lines.append("<b>Turu:</b> Duzeltilmis rapor")
        i += 1

    if i < len(parts) and WIND_RE.match(parts[i]):
        lines.append(parse_wind(parts[i]))
        i += 1

    if i < len(parts) and WIND_VAR_RE.match(parts[i]):
        m = WIND_VAR_RE.match(parts[i])
        from_dir = wind_direction_label(m.group(1))
        to_dir = wind_direction_label(m.group(2))
        lines.append(f"<b>Ruzgar Yon Degisimi:</b> {m.group(1)}\u00b0 ({from_dir}) - {m.group(2)}\u00b0 ({to_dir}) arasi")
        i += 1

    cavok = False
    if i < len(parts) and parts[i] == 'CAVOK':
        lines.append("<b>Gorunurluk:</b> 10+ km")
        lines.append("<b>Bulutlar:</b> Yok (CAVOK)")
        lines.append("<b>Hava Durumu:</b> Onemli hava olayi yok")
        cavok = True
        i += 1

    if not cavok:
        if i < len(parts):
            vis = parts[i]
            if vis == '9999':
                lines.append("<b>Gorunurluk:</b> 10+ km")
                i += 1
            elif vis.isdigit():
                lines.append(f"<b>Gorunurluk:</b> {int(vis):,} m")
                i += 1
            elif '/' in vis and 'SM' in vis:
                lines.append(f"<b>Gorunurluk:</b> {escape(vis)}")
                i += 1
            elif 'SM' in vis:
                lines.append(f"<b>Gorunurluk:</b> {escape(vis)}")
                i += 1

        cloud_items = []
        while i < len(parts):
            c = parse_cloud(parts[i])
            if c is not None:
                cloud_items.append(c)
                i += 1
            else:
                break
        if cloud_items:
            lines.append(f"<b>Bulutlar:</b> {', '.join(cloud_items)}")

        wx_items = []
        while i < len(parts):
            w = parse_weather(parts[i])
            if w is not None:
                wx_items.append(w)
                i += 1
            else:
                break
        if wx_items:
            lines.append(f"<b>Hava Durumu:</b> {', '.join(wx_items)}")

    if i < len(parts) and TEMP_RE.match(parts[i]):
        m = TEMP_RE.match(parts[i])
        i += 1
        temp = int(m.group(1).replace('M', '-'))
        dew = int(m.group(2).replace('M', '-'))
        temp_s = f"{temp}\u00b0C" if temp >= 0 else f"-{abs(temp)}\u00b0C"
        dew_s = f"{dew}\u00b0C" if dew >= 0 else f"-{abs(dew)}\u00b0C"
        rh = calc_relative_humidity(temp, dew)
        lines.append(f"<b>Sicaklik:</b> {temp_s}  |  <b>Cig Noktasi:</b> {dew_s}  |  <b>Nem:</b> %{rh}")

    if i < len(parts) and QNH_RE.match(parts[i]):
        m = QNH_RE.match(parts[i])
        i += 1
        qnh = int(m.group(1))
        inhg = qnh * 0.02953
        lines.append(f"<b>QNH:</b> {qnh} hPa ({inhg:.2f} inHg)")

    if i < len(parts) and parts[i].startswith('RE'):
        re_weather = parts[i]
        i += 1
        re_label = parse_weather(re_weather[2:])
        if re_label:
            lines.append(f"<b>Son Hava Durumu:</b> {re_label}")

    while i < len(parts):
        p = parts[i]
        if p == 'NOSIG':
            lines.append("<b>Onemli Degisiklik:</b> Beklenmiyor (NOSIG)")
            i += 1
        elif p in ('TEMPO', 'BECMG', 'FM', 'PROB'):
            trend_parts = [p]
            i += 1
            while i < len(parts) and not parts[i].startswith('RMK') and parts[i] not in ('TEMPO', 'BECMG', 'FM', 'PROB'):
                trend_parts.append(parts[i])
                i += 1
            trend_label = {'TEMPO': 'Gecici', 'BECMG': 'Donusen', 'FM': 'Buradan', 'PROB': 'Olasilik'}.get(trend_parts[0], trend_parts[0])
            lines.append(f"<b>Trend ({trend_label}):</b> {escape(' '.join(trend_parts[1:]))}")
        elif p == 'RMK':
            remarks = ' '.join(parts[i+1:])
            if remarks.strip():
                lines.append(f"<b>Notlar:</b> {escape(remarks.strip())}")
            break
        elif RUNWAY_VR_RE.match(p):
            i += 1
        else:
            i += 1

    return '\n'.join(lines)


def calc_relative_humidity(temp: int, dew: int) -> int:
    try:
        if temp < -50 or temp > 60:
            return 0
        es = 6.11 * 10.0 ** (7.5 * temp / (237.7 + temp))
        ed = 6.11 * 10.0 ** (7.5 * dew / (237.7 + dew))
        return min(100, max(0, int((ed / es) * 100)))
    except (ZeroDivisionError, OverflowError):
        return 0


def fetch_metar(icao: str) -> dict | None:
    try:
        resp = requests.get(
            METAR_API,
            params={"ids": icao, "format": "json", "taf": "false"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data and len(data) > 0:
            return data[0]
        return None
    except requests.RequestException as e:
        logger.error(f"API error for {icao}: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\u2708\ufe0f <b>METAR Bot'a hosgeldiniz!</b>\n\n"
        "Havalimani ICAO kodunu gonderin (orn: <code>LTAI</code>), guncel METAR bilgisini ileteyim.\n\n"
        "Ornekler:\n"
        "\u2022 <code>LTAI</code> - Antalya\n"
        "\u2022 <code>LTBA</code> - Istanbul\n"
        "\u2022 <code>LTFM</code> - Istanbul\n"
        "\u2022 <code>LTBJ</code> - Izmir",
        parse_mode="HTML"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if not ICAO_PATTERN.match(text):
        await update.message.reply_text(
            "\u26a0\ufe0f <b>Gecersiz ICAO kodu.</b>\n"
            "Lutfen 4 harfli bir ICAO kodu gonderin (orn: <code>LTAI</code>).",
            parse_mode="HTML"
        )
        return

    await update.message.chat.send_action("typing")

    result = fetch_metar(text)
    if result and result.get("rawOb"):
        metar_data = result["rawOb"]
        airport = result.get("icaoId", text)
        airport_name = result.get("name", "")
        decoded = parse_metar(metar_data, airport_name)
        message = (
            f"\U0001f4e1 <b>{airport} METAR Raporu</b>\n"
            "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"<b>RAW:</b>\n<code>{escape(metar_data)}</code>\n\n"
            f"\U0001f4cb <b>Detayli Rapor:</b>\n"
            f"{decoded}"
        )
        await update.message.reply_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"\u274c <b>{escape(text)}</b> icin METAR bilgisi alinamadi.\n"
            "ICAO kodunu kontrol edip tekrar deneyin.",
            parse_mode="HTML"
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
