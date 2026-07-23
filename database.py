import aiosqlite
from datetime import datetime
from config import DB_PATH, FREE_DAILY_LIMIT

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                downloads_today INTEGER DEFAULT 0,
                last_download_date TEXT,
                is_subscribed INTEGER DEFAULT 0,
                sub_end_date TEXT
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT downloads_today, last_download_date, is_subscribed FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                await db.execute(
                    "INSERT INTO users (user_id, downloads_today, last_download_date, is_subscribed) VALUES (?, 0, ?, 0)",
                    (user_id, today)
                )
                await db.commit()
                return {"downloads_today": 0, "is_subscribed": 0}
            
            downloads_today, last_date, is_subscribed = row
            
            # Если наступил новый день — сбрасываем счетчик скачиваний
            if last_date != today:
                downloads_today = 0
                await db.execute(
                    "UPDATE users SET downloads_today = 0, last_download_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
                await db.commit()
                
            return {"downloads_today": downloads_today, "is_subscribed": is_subscribed}

async def increment_downloads(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET downloads_today = downloads_today + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def activate_subscription(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_subscribed = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
