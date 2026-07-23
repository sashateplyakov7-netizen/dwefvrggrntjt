import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
FREE_DAILY_LIMIT = 3
SUB_PRICE = 100

# Никаких дефолтных строк с паролями — читаем ТОЛЬКО из переменных окружения!
DATABASE_URL = os.getenv("DATABASE_URL")
