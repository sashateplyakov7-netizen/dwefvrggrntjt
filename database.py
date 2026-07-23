import asyncpg
from datetime import datetime
from config import DATABASE_URL

# Пул соединений с Supabase
pool = None

async def init_db():
    global pool
    
    if not DATABASE_URL:
        print("❌ ОШИБКА: Переменная DATABASE_URL не найдена!")
        return

    masked_host = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "неизвестно"
    print(f"📡 Подключаемся к Supabase: ...@{masked_host}")

    # Подключение с обязательным SSL и отключенным statement_cache под Supabase Pooler
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        ssl="require",
        statement_cache_size=0
    )
    
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                downloads_today INT DEFAULT 0,
                last_download_date VARCHAR(10),
                is_subscribed INT DEFAULT 0,
                sub_end_date VARCHAR(20)
            );
        """)
    print("✅ База данных Supabase успешно инициализирована!")

async def get_or_create_user(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT downloads_today, last_download_date, is_subscribed FROM users WHERE user_id = $1", 
            user_id
        )
        
        if not row:
            await conn.execute(
                "INSERT INTO users (user_id, downloads_today, last_download_date, is_subscribed) VALUES ($1, 0, $2, 0)",
                user_id, today
            )
            return {"downloads_today": 0, "is_subscribed": 0}
        
        downloads_today = row["downloads_today"]
        last_date = row["last_download_date"]
        is_subscribed = row["is_subscribed"]
        
        # Новый день — сбрасываем счетчик
        if last_date != today:
            downloads_today = 0
            await conn.execute(
                "UPDATE users SET downloads_today = 0, last_download_date = $1 WHERE user_id = $2",
                today, user_id
            )
            
        return {"downloads_today": downloads_today, "is_subscribed": is_subscribed}

async def increment_downloads(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET downloads_today = downloads_today + 1 WHERE user_id = $1", 
            user_id
        )

async def activate_subscription(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 1 WHERE user_id = $1", 
            user_id
        )
