import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", 3))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
DATABASE_URL = os.getenv("DATABASE_URL")

# --- ПРОВЕРКА ЛОГИНА ---
if DATABASE_URL:
    try:
        user_part = DATABASE_URL.split("//")[1].split(":")[0]
        print(f"🔍 БОТ ПЫТАЕТСЯ ВОЙТИ ПОД ЛОГИНОМ: '{user_part}'")
    except Exception:
        pass

# ==========================================
# ТАРИФЫ
# ==========================================
TARIFFS = {
    "free": {
        "name": "Бесплатный",
        "price": 0,
        "daily_limit": 3,
        "platforms": ["tiktok", "instagram", "pinterest"],
        "max_duration": 60,  # секунд
        "max_size": 30,      # МБ
        "quality": "medium"
    },
    "standard": {
        "name": "Стандарт",
        "price": 100,        # 100 рублей
        "daily_limit": 30,
        "platforms": ["tiktok", "instagram", "youtube", "pinterest", "twitter", "facebook", "reddit", "vimeo"],
        "max_duration": 300,
        "max_size": 50,
        "quality": "high"
    },
    "premium": {
        "name": "Премиум",
        "price": 300,        # 300 рублей
        "daily_limit": 9999, # Безлимит
        "platforms": ["all"],
        "max_duration": 3600,
        "max_size": 200,
        "quality": "best"
    }
}

# Цены для Telegram Stars (в звёздах)
# 1 звезда = 2 рубля (комиссия Telegram ~30%)
TARIFF_STARS = {
    "standard": 50,   # 100 руб / 2 = 50 звёзд
    "premium": 150,   # 300 руб / 2 = 150 звёзд
}

# ==========================================
# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
# ==========================================
DEFAULT_TARIFF = "free"
SUB_DURATION_DAYS = 30  # Длительность подписки в днях
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ для yt-dlp
MAX_HQ_FILE_SIZE = 200 * 1024 * 1024  # 200 МБ для премиума

# ==========================================
# 🔥 ВСЕ ПОДДЕРЖИВАЕМЫЕ ПЛАТФОРМЫ
# ==========================================
SUPPORTED_PLATFORMS = [
    "tiktok.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "reddit.com",
    "vimeo.com",
    "t.me",
    "vk.com",
    "vkontakte.ru",
    "likee.com",
    "rutube.ru",
    "twitch.tv",
    "coub.com",
    "tumblr.com",
    "dailymotion.com",
    "9gag.com",
]

# ==========================================
# 🔥 ИМЯ БОТА ДЛЯ РЕФЕРАЛЬНЫХ ССЫЛОК
# ==========================================
BOT_USERNAME = "Downloader_Dowo_Bot"  # БЕЗ @

# ==========================================
# ЮMONEY (ОПЦИОНАЛЬНО)
# ==========================================
YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
YOOMONEY_REDIRECT_URI = os.getenv("YOOMONEY_REDIRECT_URI", "https://t.me/Downloader_Dowo_Bot")

# ==========================================
# ЛОГИРОВАНИЕ
# ==========================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# ==========================================
# РАЗРЕШЁННЫЕ ФОРМАТЫ
# ==========================================
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".webm", ".mkv", ".avi"]
ALLOWED_AUDIO_EXTENSIONS = [".mp3", ".m4a", ".wav"]

# ==========================================
# НАСТРОЙКИ СКАЧИВАНИЯ
# ==========================================
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 120))
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", 3))
