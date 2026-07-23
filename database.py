from datetime import timedelta
import asyncpg
from datetime import datetime
from config import DATABASE_URL, TARIFFS

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
                    tariff VARCHAR(20) DEFAULT 'free',
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
            "SELECT downloads_today, total_downloads, last_download_date, tariff, is_subscribed, sub_start_date, sub_end_date FROM users WHERE user_id = $1", 
            user_id
        )
        
        if not row:
            await conn.execute(
                "INSERT INTO users (user_id, downloads_today, total_downloads, last_download_date, tariff, is_subscribed, created_at, last_activity) VALUES ($1, 0, 0, $2, 'free', 0, $3, $3)",
                user_id, today, now
            )
            return {
                "downloads_today": 0,
                "total_downloads": 0,
                "tariff": "free",
                "is_subscribed": 0,
                "sub_start_date": None,
                "sub_end_date": None
            }
        
        downloads_today = row["downloads_today"]
        total_downloads = row["total_downloads"]
        last_date = row["last_download_date"]
        tariff = row["tariff"] or "free"
        is_subscribed = row["is_subscribed"]
        sub_start_date = row["sub_start_date"]
        sub_end_date = row["sub_end_date"]
        
        # Проверяем, не истекла ли подписка
        if is_subscribed == 1 and sub_end_date:
            if datetime.now() > datetime.strptime(sub_end_date, "%Y-%m-%d %H:%M:%S"):
                is_subscribed = 0
                tariff = "free"
                await conn.execute(
                    "UPDATE users SET is_subscribed = 0, tariff = 'free' WHERE user_id = $1",
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
            "tariff": tariff,
            "is_subscribed": is_subscribed,
            "sub_start_date": sub_start_date,
            "sub_end_date": sub_end_date
        }

async def increment_downloads(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET downloads_today = downloads_today + 1, total_downloads = total_downloads + 1, last_download_date = $1, last_activity = $2 WHERE user_id = $3",
            today, now, user_id
        )

async def activate_subscription(user_id: int, tariff_key: str = "standard"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 1, tariff = $1, sub_start_date = $2, sub_end_date = $3 WHERE user_id = $4",
            tariff_key, now, end_date, user_id
        )

async def get_user_stats(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT downloads_today, total_downloads, tariff, is_subscribed, sub_start_date, sub_end_date FROM users WHERE user_id = $1",
            user_id
        )
        
        if not row:
            return None
            
        return {
            "downloads_today": row["downloads_today"],
            "total_downloads": row["total_downloads"],
            "tariff": row["tariff"] or "free",
            "is_subscribed": row["is_subscribed"],
            "sub_start_date": row["sub_start_date"],
            "sub_end_date": row["sub_end_date"]
        }

async def get_user_tariff(user_id: int) -> str:
    """Возвращает текущий тариф пользователя"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tariff, is_subscribed, sub_end_date FROM users WHERE user_id = $1",
            user_id
        )
        if not row:
            return "free"
        
        # Проверяем, не истекла ли подписка
        if row["is_subscribed"] == 1 and row["sub_end_date"]:
            if datetime.now() > datetime.strptime(row["sub_end_date"], "%Y-%m-%d %H:%M:%S"):
                await conn.execute(
                    "UPDATE users SET is_subscribed = 0, tariff = 'free' WHERE user_id = $1",
                    user_id
                )
                return "free"
        
        return row["tariff"] if row["is_subscribed"] == 1 else "free"

async def can_download(user_id: int, platform: str) -> tuple[bool, str]:
    """
    Проверяет, может ли пользователь скачать видео с указанной платформы.
    Возвращает: (можно_скачать, сообщение_об_ошибке)
    """
    tariff_key = await get_user_tariff(user_id)
    tariff = TARIFFS.get(tariff_key, TARIFFS["free"])
    
    # Проверка платформы
    allowed_platforms = tariff.get("platforms", [])
    if allowed_platforms != ["all"] and platform not in allowed_platforms:
        return False, f"❌ Тариф «{tariff['name']}» не поддерживает {platform}.\n\n💡 Используй /tariff для смены тарифа."
    
    # Проверка лимита
    if tariff["daily_limit"] == 9999:  # Безлимит
        return True, ""
    
    user = await get_or_create_user(user_id)
    if user["downloads_today"] >= tariff["daily_limit"]:
        return False, f"❌ Лимит исчерпан ({tariff['daily_limit']}/{tariff['daily_limit']}).\n\n💡 Используй /tariff для смены тарифа."
    
    return True, ""

# ==========================================
# АДМИН-ФУНКЦИИ
# ==========================================

async def get_admin_stats():
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        active_subs = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_subscribed = 1")
        total_downloads = await conn.fetchval("SELECT COALESCE(SUM(total_downloads), 0) FROM users")
        
        # Статистика по тарифам
        free_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE tariff = 'free' OR is_subscribed = 0")
        standard_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE tariff = 'standard' AND is_subscribed = 1")
        premium_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE tariff = 'premium' AND is_subscribed = 1")
        
        return {
            "total_users": total_users,
            "active_subs": active_subs,
            "total_downloads": total_downloads,
            "free_users": free_users,
            "standard_users": standard_users,
            "premium_users": premium_users
        }

async def get_all_users():
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT user_id FROM users")
        return [record["user_id"] for record in records]

async def get_all_users_with_stats():
    async with pool.acquire() as conn:
        records = await conn.fetch(
            "SELECT user_id, downloads_today, total_downloads, tariff, is_subscribed, sub_end_date, last_activity FROM users ORDER BY total_downloads DESC"
        )
        return [
            {
                "user_id": r["user_id"],
                "downloads_today": r["downloads_today"],
                "total_downloads": r["total_downloads"],
                "tariff": r["tariff"] or "free",
                "is_subscribed": r["is_subscribed"],
                "sub_end_date": r["sub_end_date"],
                "last_activity": r["last_activity"]
            }
            for r in records
        ]

async def grant_sub_by_admin(user_id: int, tariff_key: str = "standard"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 1, tariff = $1, sub_start_date = $2, sub_end_date = $3 WHERE user_id = $4",
            tariff_key, now, end_date, user_id
        )

async def revoke_sub_by_admin(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 0, tariff = 'free', sub_start_date = NULL, sub_end_date = NULL WHERE user_id = $1",
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
            "SELECT user_id, downloads_today, total_downloads, tariff, is_subscribed, sub_end_date, last_activity FROM users WHERE user_id = $1",
            user_id
        )
        
        if not record:
            return None
            
        return {
            "user_id": record["user_id"],
            "downloads_today": record["downloads_today"],
            "total_downloads": record["total_downloads"],
            "tariff": record["tariff"] or "free",
            "is_subscribed": record["is_subscribed"],
            "sub_end_date": record["sub_end_date"],
            "last_activity": record["last_activity"]
        }

async def update_user_tariff(user_id: int, tariff_key: str):
    """Обновляет тариф пользователя (без изменения подписки)"""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET tariff = $1 WHERE user_id = $2",
            tariff_key, user_id
        )
