from datetime import timedelta
import asyncpg
from datetime import datetime
from config import DATABASE_URL, TARIFFS, SUB_DURATION_DAYS, DEFAULT_TARIFF

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
                    last_activity VARCHAR(20),
                    invited_by BIGINT DEFAULT 0,
                    referral_count INT DEFAULT 0,
                    free_standard_used INT DEFAULT 0,
                    free_premium_used INT DEFAULT 0
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
            "SELECT downloads_today, total_downloads, last_download_date, tariff, is_subscribed, sub_start_date, sub_end_date, invited_by, referral_count, free_standard_used, free_premium_used FROM users WHERE user_id = $1", 
            user_id
        )
        
        if not row:
            await conn.execute(
                "INSERT INTO users (user_id, downloads_today, total_downloads, last_download_date, tariff, is_subscribed, created_at, last_activity) VALUES ($1, 0, 0, $2, $3, 0, $4, $4)",
                user_id, today, DEFAULT_TARIFF, now
            )
            return {
                "downloads_today": 0,
                "total_downloads": 0,
                "tariff": DEFAULT_TARIFF,
                "is_subscribed": 0,
                "sub_start_date": None,
                "sub_end_date": None,
                "invited_by": 0,
                "referral_count": 0,
                "free_standard_used": 0,
                "free_premium_used": 0
            }
        
        downloads_today = row["downloads_today"]
        total_downloads = row["total_downloads"]
        last_date = row["last_download_date"]
        tariff = row["tariff"] or DEFAULT_TARIFF
        is_subscribed = row["is_subscribed"]
        sub_start_date = row["sub_start_date"]
        sub_end_date = row["sub_end_date"]
        invited_by = row["invited_by"] or 0
        referral_count = row["referral_count"] or 0
        free_standard_used = row["free_standard_used"] or 0
        free_premium_used = row["free_premium_used"] or 0
        
        # Проверяем, не истекла ли подписка
        if is_subscribed == 1 and sub_end_date:
            try:
                if datetime.now() > datetime.strptime(sub_end_date, "%Y-%m-%d %H:%M:%S"):
                    is_subscribed = 0
                    tariff = DEFAULT_TARIFF
                    await conn.execute(
                        "UPDATE users SET is_subscribed = 0, tariff = $1 WHERE user_id = $2",
                        DEFAULT_TARIFF, user_id
                    )
            except ValueError:
                is_subscribed = 0
                tariff = DEFAULT_TARIFF
                await conn.execute(
                    "UPDATE users SET is_subscribed = 0, tariff = $1 WHERE user_id = $2",
                    DEFAULT_TARIFF, user_id
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
            "sub_end_date": sub_end_date,
            "invited_by": invited_by,
            "referral_count": referral_count,
            "free_standard_used": free_standard_used,
            "free_premium_used": free_premium_used
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
    end_date = (datetime.now() + timedelta(days=SUB_DURATION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_subscribed = 1, tariff = $1, sub_start_date = $2, sub_end_date = $3 WHERE user_id = $4",
            tariff_key, now, end_date, user_id
        )

async def get_user_stats(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT downloads_today, total_downloads, tariff, is_subscribed, sub_start_date, sub_end_date, invited_by, referral_count, free_standard_used, free_premium_used FROM users WHERE user_id = $1",
            user_id
        )
        
        if not row:
            return None
            
        return {
            "downloads_today": row["downloads_today"],
            "total_downloads": row["total_downloads"],
            "tariff": row["tariff"] or DEFAULT_TARIFF,
            "is_subscribed": row["is_subscribed"],
            "sub_start_date": row["sub_start_date"],
            "sub_end_date": row["sub_end_date"],
            "invited_by": row["invited_by"] or 0,
            "referral_count": row["referral_count"] or 0,
            "free_standard_used": row["free_standard_used"] or 0,
            "free_premium_used": row["free_premium_used"] or 0
        }

async def get_user_tariff(user_id: int) -> str:
    """Возвращает текущий тариф пользователя"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tariff, is_subscribed, sub_end_date FROM users WHERE user_id = $1",
            user_id
        )
        if not row:
            return DEFAULT_TARIFF
        
        if row["is_subscribed"] == 1 and row["sub_end_date"]:
            try:
                if datetime.now() > datetime.strptime(row["sub_end_date"], "%Y-%m-%d %H:%M:%S"):
                    await conn.execute(
                        "UPDATE users SET is_subscribed = 0, tariff = $1 WHERE user_id = $2",
                        DEFAULT_TARIFF, user_id
                    )
                    return DEFAULT_TARIFF
            except ValueError:
                await conn.execute(
                    "UPDATE users SET is_subscribed = 0, tariff = $1 WHERE user_id = $2",
                    DEFAULT_TARIFF, user_id
                )
                return DEFAULT_TARIFF
        
        return row["tariff"] if row["is_subscribed"] == 1 else DEFAULT_TARIFF

async def can_download(user_id: int, platform: str) -> tuple[bool, str]:
    tariff_key = await get_user_tariff(user_id)
    tariff = TARIFFS.get(tariff_key, TARIFFS.get(DEFAULT_TARIFF))
    
    if not tariff:
        tariff = TARIFFS[DEFAULT_TARIFF]
    
    allowed_platforms = tariff.get("platforms", [])
    if allowed_platforms != ["all"] and platform not in allowed_platforms:
        return False, f"❌ Тариф «{tariff['name']}» не поддерживает {platform}.\n\n💡 Используй кнопку 'Выбрать тариф' для смены."
    
    if tariff["daily_limit"] == 9999:
        return True, ""
    
    user = await get_or_create_user(user_id)
    if user["downloads_today"] >= tariff["daily_limit"]:
        return False, f"❌ Лимит исчерпан ({tariff['daily_limit']}/{tariff['daily_limit']}).\n\n💡 Используй кнопку 'Выбрать тариф' для смены."
    
    return True, ""

async def get_user_download_limit(user_id: int) -> int:
    tariff_key = await get_user_tariff(user_id)
    tariff = TARIFFS.get(tariff_key, TARIFFS.get(DEFAULT_TARIFF))
    return tariff.get("daily_limit", 3)

# ==========================================
# 🔥 РЕФЕРАЛЬНАЯ СИСТЕМА
# ==========================================

async def generate_referral_link(user_id: int) -> str:
    """Генерирует реферальную ссылку"""
    bot_username = "ваш_бот"  # Замени на своего бота
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

async def process_referral(new_user_id: int, referrer_id: int) -> str:
    """
    Обрабатывает переход по реферальной ссылке.
    Возвращает сообщение о награде.
    """
    if new_user_id == referrer_id:
        return "❌ Нельзя пригласить самого себя!"
    
    async with pool.acquire() as conn:
        # Проверяем, не был ли уже приглашён пользователь
        new_user = await conn.fetchrow(
            "SELECT invited_by FROM users WHERE user_id = $1",
            new_user_id
        )
        if new_user and new_user["invited_by"] != 0:
            return "ℹ️ Ты уже был приглашён другим пользователем."
        
        # Связываем нового пользователя с реферером
        await conn.execute(
            "UPDATE users SET invited_by = $1 WHERE user_id = $2",
            referrer_id, new_user_id
        )
        
        # Обновляем счётчик рефералов у реферера
        await conn.execute(
            "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = $1",
            referrer_id
        )
        
        # Получаем текущее количество рефералов
        referrer = await conn.fetchrow(
            "SELECT referral_count, free_standard_used, free_premium_used FROM users WHERE user_id = $1",
            referrer_id
        )
        
        count = referrer["referral_count"] if referrer else 0
        messages = []
        
        # 🎁 Награда за 1 реферала — Стандарт на месяц
        if count >= 1 and referrer and referrer["free_standard_used"] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            
            await conn.execute(
                "UPDATE users SET free_standard_used = 1, tariff = 'standard', is_subscribed = 1, sub_start_date = $1, sub_end_date = $2 WHERE user_id = $3",
                now, end_date, referrer_id
            )
            messages.append("🎁 **Ты получил тариф СТАНДАРТ на 30 дней за 1 приглашение!**")
        
        # 💎 Награда за 3 реферала — Премиум на месяц
        if count >= 3 and referrer and referrer["free_premium_used"] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Обновляем на Премиум, если он ещё не активен
            await conn.execute(
                "UPDATE users SET free_premium_used = 1, tariff = 'premium', is_subscribed = 1, sub_start_date = $1, sub_end_date = $2 WHERE user_id = $3",
                now, end_date, referrer_id
            )
            messages.append("💎 **Ты получил тариф ПРЕМИУМ на 30 дней за 3 приглашения!**")
        
        if not messages:
            messages.append(f"✅ Ты пригласил друга! У тебя {count} приглашений. Осталось {3 - count} до Премиума.")
        
        return "\n\n".join(messages)

async def get_referral_info(user_id: int) -> dict:
    """Возвращает информацию о рефералах пользователя"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT referral_count, free_standard_used, free_premium_used FROM users WHERE user_id = $1",
            user_id
        )
        
        if not row:
            return {"count": 0, "standard_used": False, "premium_used": False}
        
        return {
            "count": row["referral_count"] or 0,
            "standard_used": row["free_standard_used"] == 1,
            "premium_used": row["free_premium_used"] == 1
        }

# ==========================================
# АДМИН-ФУНКЦИИ
# ==========================================

async def get_admin_stats():
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        active_subs = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_subscribed = 1")
        total_downloads = await conn.fetchval("SELECT COALESCE(SUM(total_downloads), 0) FROM users")
        
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
            "SELECT user_id, downloads_today, total_downloads, tariff, is_subscribed, sub_end_date, last_activity, referral_count FROM users ORDER BY total_downloads DESC"
        )
        return [
            {
                "user_id": r["user_id"],
                "downloads_today": r["downloads_today"],
                "total_downloads": r["total_downloads"],
                "tariff": r["tariff"] or DEFAULT_TARIFF,
                "is_subscribed": r["is_subscribed"],
                "sub_end_date": r["sub_end_date"],
                "last_activity": r["last_activity"],
                "referral_count": r["referral_count"] or 0
            }
            for r in records
        ]

async def grant_sub_by_admin(user_id: int, tariff_key: str = "standard"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_date = (datetime.now() + timedelta(days=SUB_DURATION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    
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
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM users WHERE last_activity < $1 AND is_subscribed = 0 AND total_downloads = 0",
            cutoff
        )
        return result.split()[1]

async def search_users_by_id(user_id: int):
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT user_id, downloads_today, total_downloads, tariff, is_subscribed, sub_end_date, last_activity, referral_count FROM users WHERE user_id = $1",
            user_id
        )
        
        if not record:
            return None
            
        return {
            "user_id": record["user_id"],
            "downloads_today": record["downloads_today"],
            "total_downloads": record["total_downloads"],
            "tariff": record["tariff"] or DEFAULT_TARIFF,
            "is_subscribed": record["is_subscribed"],
            "sub_end_date": record["sub_end_date"],
            "last_activity": record["last_activity"],
            "referral_count": record["referral_count"] or 0
        }

async def update_user_tariff(user_id: int, tariff_key: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET tariff = $1 WHERE user_id = $2",
            tariff_key, user_id
        )
