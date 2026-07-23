from datetime import timedelta
import asyncpg
from datetime import datetime
from config import DATABASE_URL

# Глобальный пул соединений
pool = None

async def init_db():
    global pool
    
    if not DATABASE_URL:
        print("❌ ОШИБКА: Переменная DATABASE_URL пуста или не найдена в Render!", flush=True)
        return

    try:
        masked = DATABASE_URL.split("@")[-1]
        print(f"📡 Подключаемся к базе: {masked}", flush=True)
    except Exception:
        print("📡 Подключаемся к базе...", flush=True)

    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            ssl="require",
            statement_cache_size=0,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    downloads_today INT DEFAULT 0,
                    total_downloads INT DEFAULT 0,
                    last_download_date VARCHAR(10),
                    is_subscribed INT DEFAULT 0,
                    sub_start_date VARCHAR(20),
                    sub_end_date VARCHAR(20),
                    created_at VARCHAR(20),
                    last_activity VARCHAR(20)
                );
            """)
        print("✅ База данных успешно подключена и таблицы созданы!", flush=True)
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}", flush=True)
        raise e

# ==========================================
# ОСНОВНЫЕ ФУНКЦИИ
# ==========================================

async def get_or_create_user(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT downloads_today, total_downloads, last_download_date, is_subscribed, sub_start_date, sub_end_date FROM users WHERE user_id = $1", 
            user_id
        )
        
        if not row:
            await conn.execute(
                "INSERT INTO users (user_id, downloads_today, total_downloads, last_download_date, is_subscribed, created_at, last_activity) VALUES ($1, 0, 0, $2, 0, $3, $3)",
                user_id, today, now
            )
            return {
                "downloads_today": 0,
                "total_downloads": 0,
                "is_subscribed": 0,
                "sub_start_date": None,
                "sub_end_date": None
            }
        
        downloads_today = row["downloads_today"]
        total_downloads = row["total_downloads"]
        last_date = row["last_download_date"]
        is_subscribed = row["is_subscribed"]
        sub_start_date = row["sub_start_date"]
        sub_end_date = row["sub_end_date"]
        
        # Проверяем, не истекла ли подписка
        if is_subscribed == 1 and sub_end_date:
            if datetime.now() > datetime.strptime(sub_end_date, "%Y-%m-%d %H:%M:%S"):
                is_subscribed = 0
                await conn.execute(
                    "UPDATE users SET is_subscribed = 0 WHERE user_id = $1",
                    user_id
                )
        
        # Новый день — сбрасываем счетчик
        if last_date != today:
            downloads_today = 0
            await conn.execute(
                "UPDATE users SET downloads_today = 0, last_download_date = $1 WHERE user_id = $2",
                today, user_id
            )
            
        return {
            "downloads_today": downloads_today,
            "total_downloads": total_downloads,
            "is_subscribed": is_subscribed,
            "sub_start_date": sub_start_date,
            "sub_end_date": sub_end_date
        }

async def increment_downloads(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET downloads_today = downloads_today + 1, total_downloads = total_downloads + 1, last_activity = $1 WHERE user_id = $2",
            now, user_id
        )

async def activate_subscription(user_id: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 1, sub_start_date = $1, sub_end_date = $2 WHERE user_id = $3",
            now, end_date, user_id
        )

async def get_user_stats(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT downloads_today, total_downloads, is_subscribed, sub_start_date, sub_end_date FROM users WHERE user_id = $1",
            user_id
        )
        
        if not row:
            return None
            
        return {
            "downloads_today": row["downloads_today"],
            "total_downloads": row["total_downloads"],
            "is_subscribed": row["is_subscribed"],
            "sub_start_date": row["sub_start_date"],
            "sub_end_date": row["sub_end_date"]
        }

# ==========================================
# АДМИН-ФУНКЦИИ
# ==========================================

async def get_admin_stats():
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        active_subs = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_subscribed = 1")
        total_downloads = await conn.fetchval("SELECT COALESCE(SUM(total_downloads), 0) FROM users")
        
        return {
            "total_users": total_users,
            "active_subs": active_subs,
            "total_downloads": total_downloads
        }

async def get_all_users():
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT user_id FROM users")
        return [record["user_id"] for record in records]

async def get_all_users_with_stats():
    async with pool.acquire() as conn:
        records = await conn.fetch(
            "SELECT user_id, downloads_today, total_downloads, is_subscribed, sub_end_date, last_activity FROM users ORDER BY total_downloads DESC"
        )
        return [
            {
                "user_id": r["user_id"],
                "downloads_today": r["downloads_today"],
                "total_downloads": r["total_downloads"],
                "is_subscribed": r["is_subscribed"],
                "sub_end_date": r["sub_end_date"],
                "last_activity": r["last_activity"]
            }
            for r in records
        ]

async def grant_sub_by_admin(user_id: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 1, sub_start_date = $1, sub_end_date = $2 WHERE user_id = $3",
            now, end_date, user_id
        )

async def revoke_sub_by_admin(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 0, sub_start_date = NULL, sub_end_date = NULL WHERE user_id = $1",
            user_id
        )

async def get_top_users(limit: int = 10):
    async with pool.acquire() as conn:
        records = await conn.fetch(
            "SELECT user_id, total_downloads FROM users ORDER BY total_downloads DESC LIMIT $1",
            limit
        )
        return [{"user_id": r["user_id"], "total_downloads": r["total_downloads"]} for r in records]

async def cleanup_inactive_users():
    """Удаляет пользователей, которые не активны более 30 дней"""
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM users WHERE last_activity < $1 AND is_subscribed = 0 AND total_downloads = 0",
            cutoff
        )
        return result.split()[1]  # Возвращает количество удалённых строк

async def search_users_by_id(user_id: int):
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT user_id, downloads_today, total_downloads, is_subscribed, sub_end_date, last_activity FROM users WHERE user_id = $1",
            user_id
        )
        
        if not record:
            return None
            
        return {
            "user_id": record["user_id"],
            "downloads_today": record["downloads_today"],
            "total_downloads": record["total_downloads"],
            "is_subscribed": record["is_subscribed"],
            "sub_end_date": record["sub_end_date"],
            "last_activity": record["last_activity"]
        }
