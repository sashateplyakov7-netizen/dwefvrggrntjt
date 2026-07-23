import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
FREE_DAILY_LIMIT = 3
SUB_PRICE = 100

DATABASE_URL = os.getenv("DATABASE_URL")

# --- ПРОВЕРКА ЛОГИНА ---
if DATABASE_URL:
    try:
        user_part = DATABASE_URL.split("//")[1].split(":")[0]
        print(f"🔍 БОТ ПЫТАЕТСЯ ВОЙТИ ПОД ЛОГИНОМ: '{user_part}'")
    except Exception:
        pass
