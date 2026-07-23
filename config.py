Python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_ОТ_BOTFATHER")
FREE_DAILY_LIMIT = 3   # Бесплатные скачивания в день
SUB_PRICE = 100        # Цена подписки в рублях
DB_PATH = "bot_database.db"
