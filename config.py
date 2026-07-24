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
        "max_duration": 60,
        "max_size": 30,
        "quality": "medium"
    },
    "standard": {
        "name": "Стандарт",
        "price": 1,
        "daily_limit": 30,
        # 🔥 5 ПЛАТФОРМ (БЕЗ YOUTUBE!)
        "platforms": ["tiktok", "instagram", "pinterest", "twitter", "facebook"],
        "max_duration": 300,
        "max_size": 50,
        "quality": "high"
    },
    "premium": {
        "name": "Премиум",
        "price": 1,
        "daily_limit": 9999,
        # 🔥 ВСЕ ПЛАТФОРМЫ (ПОЛНЫЙ СПИСОК)
        "platforms": [
            "tiktok",
            "instagram",
            "youtube",
            "pinterest",
            "twitter",
            "facebook",
            "reddit",
            "vimeo",
            "t.me",
            "vk",
            "likee",
            "rutube",
            "twitch",
            "coub",
            "tumblr",
            "dailymotion",
            "9gag"
        ],
        "max_duration": 3600,
        "max_size": 200,
        "quality": "best"
    }
}

# Цены для Telegram Stars
TARIFF_STARS = {
    "standard": 50,
    "premium": 150,
}

# ==========================================
# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
# ==========================================
DEFAULT_TARIFF = "free"
SUB_DURATION_DAYS = 30
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_HQ_FILE_SIZE = 200 * 1024 * 1024

# ==========================================
# 🔥 ВСЕ ПОДДЕРЖИВАЕМЫЕ ПЛАТФОРМЫ (ДЛЯ DETECT_PLATFORM)
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
BOT_USERNAME = "Downloader_Dowo_Bot"

# ==========================================
# 💳 ЮMONEY
# ==========================================
YOOMONEY_SHOP_ID = os.getenv("YOOMONEY_SHOP_ID")
YOOMONEY_SECRET_KEY = os.getenv("YOOMONEY_SECRET_KEY")
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
