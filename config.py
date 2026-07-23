import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
FREE_DAILY_LIMIT = 3
SUB_PRICE = 100
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
        "price": 100,  # 100 рублей
        "daily_limit": 30,
        "platforms": ["tiktok", "instagram", "youtube", "pinterest", "twitter", "facebook"],
        "max_duration": 300,
        "max_size": 50,
        "quality": "high"
    },
    "premium": {
        "name": "Премиум",
        "price": 200,  # 200 рублей
        "daily_limit": 9999,
        "platforms": ["all"],
        "max_duration": 3600,
        "max_size": 200,
        "quality": "best"
    }
}

# Цены для Telegram Stars (в звёздах)
TARIFF_STARS = {
    "standard": int(100 / 2),  # 50 звёзд
    "premium": int(200 / 2),   # 100 звёзд
}
