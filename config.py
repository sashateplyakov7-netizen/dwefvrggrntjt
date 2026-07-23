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
        "platforms": ["tiktok", "instagram", "youtube", "pinterest", "twitter", "facebook"],
        "max_duration": 300,
        "max_size": 50,
        "quality": "high"
    },
    "premium": {
        "name": "Премиум",
        "price": 200,        # 200 рублей
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
    "premium": 100,   # 200 руб / 2 = 100 звёзд
}

# ==========================================
# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
# ==========================================
DEFAULT_TARIFF = "free"
SUB_DURATION_DAYS = 30  # Длительность подписки в днях
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ для yt-dlp
SUPPORTED_PLATFORMS = ["tiktok", "instagram", "youtube", "pinterest", "twitter", "facebook", "reddit", "vimeo"]
