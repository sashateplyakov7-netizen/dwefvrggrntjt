import asyncio
import os
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, FREE_DAILY_LIMIT, ADMIN_ID, TARIFFS, TARIFF_STARS, BOT_USERNAME
from database import (
    init_db, get_or_create_user, increment_downloads, activate_subscription,
    get_admin_stats, grant_sub_by_admin, revoke_sub_by_admin, get_all_users,
    get_user_stats, get_user_tariff, can_download,
    generate_referral_link, process_referral, get_referral_info
)
from downloader import download_media, detect_platform, extract_video_info

# ==========================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==========================================
logging.basicConfig(level=logging.INFO)

# ==========================================
# НАСТРОЙКА СЕССИИ
# ==========================================
session = AiohttpSession(timeout=300)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# ==========================================
# FSM СОСТОЯНИЯ
# ==========================================
class AdminState(StatesGroup):
    waiting_for_broadcast_msg = State()
    waiting_for_give_sub_id = State()
    waiting_for_revoke_sub_id = State()
    waiting_for_answer = State()
    waiting_for_answer_to_user = State()

# ==========================================
# КЛАВИАТУРЫ
# ==========================================

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="show_tariffs")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton(text="📞 Связаться с админом", callback_data="contact_admin")]
    ])

def get_tariff_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Бесплатный — 0 ₽", callback_data="tariff_free"),
            InlineKeyboardButton(text="⚡ Стандарт — 100 ₽", callback_data="tariff_standard")
        ],
        [InlineKeyboardButton(text="💎 Премиум — 300 ₽", callback_data="tariff_premium")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="main_menu")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(text="🎁 Выдать сабку", callback_data="admin_give_sub"),
            InlineKeyboardButton(text="❌ Забрать сабку", callback_data="admin_revoke_sub")
        ],
        [InlineKeyboardButton(text="💬 Ответить юзеру", callback_data="admin_answer")],
        [InlineKeyboardButton(text="📦 Экспорт базы", callback_data="admin_export")],
        [InlineKeyboardButton(text="🔄 Сбросить действие", callback_data="admin_cancel")]
    ])

def get_user_stats_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="show_tariffs")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

# ==========================================
# 🔥 ФУНКЦИЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ВИДЕО
# ==========================================
async def get_video_info(url: str) -> dict:
    """
    Получает информацию о видео без скачивания.
    Возвращает словарь с названием, длительностью, размером и платформой.
    """
    try:
        info = await asyncio.to_thread(extract_video_info, url)
        
        if not info or info.get("extractor") == "unknown":
            return None
        
        duration_sec = info.get("duration", 0)
        estimated_size_mb = (duration_sec * 5) / 8  # 5 Мбит/с -> МБ
        
        return {
            "title": info.get("title", "Неизвестно")[:50],
            "duration": duration_sec,
            "duration_str": f"{duration_sec // 60}:{duration_sec % 60:02d}",
            "estimated_size_mb": round(estimated_size_mb, 1),
            "platform": info.get("platform", "unknown"),
            "thumbnail": info.get("thumbnail"),
            "extractor": info.get("extractor", "unknown")
        }
    except Exception as e:
        print(f"❌ Ошибка получения информации: {e}")
        return None

# ==========================================
# 🚀 КОМАНДА /TARIFF
# ==========================================
@dp.message(Command("tariff"))
async def cmd_tariff(message: types.Message):
    await message.answer(
        "💎 **Выбери свой тариф:**\n\n"
        "📱 **Бесплатный** — 0 ₽\n"
        "   • 3 скачивания в день\n"
        "   • TikTok, Instagram, Pinterest\n"
        "   • Качество: среднее\n\n"
        "⚡ **Стандарт** — 100 ₽/мес\n"
        "   • 30 скачиваний в день\n"
        "   • Все основные платформы\n"
        "   • Качество: высокое\n\n"
        "💎 **Премиум** — 300 ₽/мес\n"
        "   • Безлимит скачиваний\n"
        "   • Все платформы (18+)\n"
        "   • Максимальное качество (4K)\n"
        "   • Поддержка видео до 200 МБ\n"
        "   • Умный кэш (мгновенная выдача)\n"
        "   • AI-описание и хештеги\n"
        "   • Расшифровка аудио в текст",
        parse_mode="Markdown",
        reply_markup=get_tariff_keyboard()
    )

# ==========================================
# 🚀 КОМАНДА /STATS
# ==========================================
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    stats = await get_user_stats(user_id)
    tariff = await get_user_tariff(user_id)
    tariff_info = TARIFFS.get(tariff, TARIFFS["free"])
    referral_info = await get_referral_info(user_id)
    
    if stats:
        text = (
            "📊 **Твоя статистика:**\n\n"
            f"📥 Скачиваний сегодня: {stats['downloads_today']}\n"
            f"📅 Всего скачиваний: {stats['total_downloads']}\n"
            f"💎 Тариф: **{tariff_info['name']}**\n"
            f"📊 Статус: {'🟢 Активна' if stats['is_subscribed'] == 1 else '🔴 Не активна'}\n"
            f"📅 Действует до: {stats['sub_end_date'] or 'Нет'}\n\n"
            f"📱 Доступно платформ: {len(tariff_info['platforms']) if tariff_info['platforms'] != ['all'] else 'Все'}\n"
            f"📊 Лимит в день: {tariff_info['daily_limit'] if tariff_info['daily_limit'] != 9999 else '∞'}\n\n"
            f"🎁 **Рефералы:**\n"
            f"• Приглашено: {referral_info['count']} друзей\n"
            f"• Награда за 1 друга: {'✅ Получен' if referral_info['standard_used'] else '❌ Не получен'}\n"
            f"• Награда за 3 друзей: {'✅ Получен' if referral_info['premium_used'] else '❌ Не получен'}\n"
        )
    else:
        text = "⚠️ Не удалось получить данные."
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_user_stats_keyboard())

# ==========================================
# 🚀 КОМАНДА /HELP
# ==========================================
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📜 **Команды бота:**\n\n"
        "/start — Главное меню\n"
        "/tariff — Выбрать тариф\n"
        "/stats — Моя статистика\n"
        "/referral — Пригласить друга\n"
        "/admin — Панель управления (админ)\n"
        "/help — Эта справка\n\n"
        "🔗 Просто отправь ссылку на видео — я скачаю его!\n\n"
        "🎁 **Реферальная программа:**\n"
        "• Пригласи 1 друга → получи Стандарт на месяц\n"
        "• Пригласи 3 друзей → получи Премиум на месяц\n\n"
        "📱 Поддерживаемые платформы:\n"
        "• TikTok\n"
        "• Instagram (Reels, видео)\n"
        "• YouTube (Shorts, видео)\n"
        "• Pinterest\n"
        "• Twitter/X\n"
        "• Facebook\n"
        "• Reddit\n"
        "• Vimeo",
        parse_mode="Markdown"
    )

# ==========================================
# 🚀 КОМАНДА /REFERRAL
# ==========================================
@dp.message(Command("referral"))
async def cmd_referral(message: types.Message):
    user_id = message.from_user.id
    link = await generate_referral_link(user_id)
    referral_info = await get_referral_info(user_id)
    
    next_reward = ""
    if referral_info["count"] < 1:
        next_reward = "🎯 Пригласи 1 друга → Стандарт на месяц"
    elif referral_info["count"] < 3:
        next_reward = "🎯 Пригласи ещё 3 друзей → Премиум на месяц"
    else:
        next_reward = "🏆 Ты уже получил все награды!"
    
    await message.answer(
        "🎁 **Реферальная программа**\n\n"
        "Отправь другу эту ссылку:\n"
        f"`{link}`\n\n"
        "📊 **Твоя статистика:**\n"
        f"• Приглашено: {referral_info['count']} друзей\n"
        f"• Стандарт: {'✅ Получен' if referral_info['standard_used'] else '❌ Не получен'}\n"
        f"• Премиум: {'✅ Получен' if referral_info['premium_used'] else '❌ Не получен'}\n\n"
        f"{next_reward}\n\n"
        "💡 Нажми на ссылку, чтобы скопировать!",
        parse_mode="Markdown"
    )

# ==========================================
# 🚀 КОМАНДА /START
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != user_id:
                result = await process_referral(user_id, referrer_id)
                if result:
                    await message.answer(result, parse_mode="Markdown")
            else:
                await message.answer("❌ Нельзя пригласить самого себя!")
        except ValueError:
            pass
    
    await get_or_create_user(user_id)
    await message.answer(
        "👋 **Салют! Я качаю видео без водяных знаков** из TikTok, Reels, Shorts и Pinterest!\n\n"
        "🔗 Просто отправь мне ссылку на видео.\n"
        f"📊 Твой лимит: {FREE_DAILY_LIMIT} бесплатных скачиваний в день.\n\n"
        "ℹ️ *Поддерживаемые платформы:* TikTok, Instagram, YouTube, Pinterest, Twitter/X, Facebook\n\n"
        "🎁 **Пригласи друга — получи подписку!**\n"
        "• 1 друг → Стандарт на месяц\n"
        "• 3 друга → Премиум на месяц\n\n"
        "💡 Для большего выбери подходящий тариф!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==========================================
# 🚀 РЕФЕРАЛЬНАЯ КНОПКА
# ==========================================
@dp.callback_query(F.data == "referral")
async def referral_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    link = await generate_referral_link(user_id)
    referral_info = await get_referral_info(user_id)
    
    next_reward = ""
    if referral_info["count"] < 1:
        next_reward = "🎯 Пригласи 1 друга → Стандарт на месяц"
    elif referral_info["count"] < 3:
        next_reward = "🎯 Пригласи ещё 3 друзей → Премиум на месяц"
    else:
        next_reward = "🏆 Ты уже получил все награды!"
    
    await callback.message.edit_text(
        "🎁 **Реферальная программа**\n\n"
        "Отправь другу эту ссылку:\n"
        f"`{link}`\n\n"
        "📊 **Твоя статистика:**\n"
        f"• Приглашено: {referral_info['count']} друзей\n"
        f"• Стандарт: {'✅ Получен' if referral_info['standard_used'] else '❌ Не получен'}\n"
        f"• Премиум: {'✅ Получен' if referral_info['premium_used'] else '❌ Не получен'}\n\n"
        f"{next_reward}\n\n"
        "💡 Нажми на ссылку, чтобы скопировать!",
        parse_mode="Markdown"
    )
    await callback.answer()

# ==========================================
# 🚀 КОМАНДА /ADMIN
# ==========================================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав для выполнения этой команды.")
        return
    
    await state.clear()
    await message.answer(
        "👑 **Админ-панель**",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

# ==========================================
# 🚀 ОБРАБОТЧИКИ КНОПОК
# ==========================================

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 **Главное меню**\n\n"
        "Отправь ссылку на видео — я скачаю его!\n\n"
        f"📊 Твой лимит: {FREE_DAILY_LIMIT} скачиваний в день.\n\n"
        "🎁 Пригласи друга → получи подписку!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "show_tariffs")
async def show_tariffs(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💎 **Тарифы**\n\n"
        "📱 **Бесплатный** — 0 ₽\n"
        "   • 3 скачивания в день\n\n"
        "⚡ **Стандарт** — 100 ₽/мес\n"
        "   • 30 скачиваний в день\n\n"
        "💎 **Премиум** — 300 ₽/мес\n"
        "   • Безлимит\n"
        "   • Все платформы\n"
        "   • 4K, 200 МБ, AI-фишки",
        parse_mode="Markdown",
        reply_markup=get_tariff_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "my_stats")
async def my_stats_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stats = await get_user_stats(user_id)
    tariff = await get_user_tariff(user_id)
    tariff_info = TARIFFS.get(tariff, TARIFFS["free"])
    referral_info = await get_referral_info(user_id)
    
    if stats:
        text = (
            "📊 **Твоя статистика**\n\n"
            f"📥 Сегодня: {stats['downloads_today']}\n"
            f"📅 Всего: {stats['total_downloads']}\n"
            f"💎 Тариф: **{tariff_info['name']}**\n"
            f"📊 Статус: {'🟢 Активна' if stats['is_subscribed'] == 1 else '🔴 Не активна'}\n"
            f"📅 Действует до: {stats['sub_end_date'] or 'Нет'}\n\n"
            f"🎁 Приглашено: {referral_info['count']} друзей"
        )
    else:
        text = "⚠️ Не удалось получить данные."
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_user_stats_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "contact_admin")
async def contact_admin_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 **Напиши сообщение администратору.**"
    )
    await state.set_state(AdminState.waiting_for_answer)
    await callback.answer()

@dp.message(AdminState.waiting_for_answer)
async def process_user_message_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.full_name or "Пользователь"
    
    text = (
        f"💬 **Сообщение от пользователя**\n\n"
        f"👤 {user_name}\n"
        f"🆔 `{user_id}`\n\n"
        f"📝 {message.text}"
    )
    
    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=text, parse_mode="Markdown")
    elif message.video:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=text, parse_mode="Markdown")
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=text, parse_mode="Markdown")
    else:
        await bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    
    await message.answer("✅ Сообщение отправлено администратору!")
    await state.clear()

# ==========================================
# 🚀 АДМИН-ОБРАБОТЧИКИ
# ==========================================
@dp.callback_query(F.data.startswith("admin_"))
async def process_admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    action = callback.data.split("_")[1]

    if action == "stats":
        stats = await get_admin_stats()
        text = (
            "📊 **Статистика**\n\n"
            f"👥 Всего юзеров: **{stats['total_users']}**\n"
            f"💎 Подписок: **{stats['active_subs']}**\n"
            f"📥 Скачиваний: **{stats['total_downloads']}**\n\n"
            f"📱 Бесплатный: {stats.get('free_users', 0)}\n"
            f"⚡ Стандарт: {stats.get('standard_users', 0)}\n"
            f"💎 Премиум: {stats.get('premium_users', 0)}"
        )
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

    elif action == "broadcast":
        await callback.message.answer("📢 Отправь сообщение для рассылки:")
        await state.set_state(AdminState.waiting_for_broadcast_msg)

    elif action == "give":
        await callback.message.answer("🎁 Отправь: `ID тариф`")
        await state.set_state(AdminState.waiting_for_give_sub_id)

    elif action == "revoke":
        await callback.message.answer("❌ Отправь ID пользователя:")
        await state.set_state(AdminState.waiting_for_revoke_sub_id)

    elif action == "answer":
        await callback.message.answer("💬 Напиши: `user_id|сообщение`")
        await state.set_state(AdminState.waiting_for_answer_to_user)

    elif action == "export":
        await export_database(callback.message)
        return

    elif action == "cancel":
        await state.clear()
        await callback.message.edit_text("🔄 Отменено.", reply_markup=get_admin_keyboard())
        
    await callback.answer()

@dp.message(AdminState.waiting_for_broadcast_msg)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    users = await get_all_users()
    success_count = 0
    
    await message.answer(f"⏳ Начинаю рассылку для {len(users)} юзеров...")
    
    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
            
    await message.answer(f"✅ Рассылка завершена!\nУспешно: {success_count} из {len(users)}")
    await state.clear()

@dp.message(AdminState.waiting_for_give_sub_id)
async def process_give_sub(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Формат: `ID тариф`")
        return
    
    try:
        target_id = int(parts[0])
        tariff_key = parts[1] if len(parts) > 1 else "standard"
        
        if tariff_key not in ["standard", "premium"]:
            await message.answer("⚠️ Тариф: standard или premium")
            return
        
        await grant_sub_by_admin(target_id, tariff_key)
        await message.answer(f"✅ Пользователю `{target_id}` выдан тариф `{tariff_key}`!")
    except ValueError:
        await message.answer("⚠️ ID должен быть числом.")
    
    await state.clear()

@dp.message(AdminState.waiting_for_revoke_sub_id)
async def process_revoke_sub(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    if not message.text.isdigit():
        await message.answer("⚠️ ID должен состоять только из цифр.")
        return
        
    target_id = int(message.text)
    await revoke_sub_by_admin(target_id)
    await message.answer(f"❌ У пользователя `{target_id}` забрали подписку.", parse_mode="Markdown")
    await state.clear()

@dp.message(AdminState.waiting_for_answer_to_user)
async def process_answer_to_user(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text
    if "|" not in text:
        await message.answer("⚠️ Формат: `user_id|сообщение`")
        return
    
    try:
        user_id_str, answer_text = text.split("|", 1)
        user_id = int(user_id_str.strip())
        answer_text = answer_text.strip()
        
        if not answer_text:
            await message.answer("❌ Текст не может быть пустым.")
            return
        
        await bot.send_message(
            user_id,
            f"💬 **Ответ от администратора:**\n\n{answer_text}"
        )
        await message.answer(f"✅ Ответ отправлен пользователю `{user_id}`")
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
    
    await state.clear()

# ==========================================
# 🚀 ЭКСПОРТ
# ==========================================
async def export_database(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        users = await get_all_users()
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_users": len(users),
            "users": []
        }
        
        for user_id in users:
            stats = await get_user_stats(user_id)
            if stats:
                export_data["users"].append(stats)
        
        import json
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        with open(filename, "rb") as f:
            await message.answer_document(
                FSInputFile(filename),
                caption=f"📦 Экспорт базы данных\nВсего: {len(users)} пользователей"
            )
        
        os.remove(filename)
        
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")

# ==========================================
# 🚀 ТАРИФЫ И ОПЛАТА
# ==========================================
@dp.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: types.CallbackQuery):
    tariff_key = callback.data.replace("tariff_", "")
    
    if tariff_key == "free":
        await callback.message.edit_text(
            "📱 **Бесплатный тариф активен!**\n\n"
            "3 скачивания в день.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return
    
    tariff = TARIFFS.get(tariff_key)
    if not tariff:
        await callback.answer("❌ Тариф не найден")
        return
    
    price = tariff["price"]
    stars_amount = int(price / 2)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подписка «{tariff['name']}»",
        description=f"Тариф {tariff['name']} на 30 дней.\n"
                    f"Лимит: {tariff['daily_limit']} скачиваний/день",
        payload=f"sub_{tariff_key}_payload",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Подписка {tariff['name']} на месяц", amount=stars_amount)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    tariff_key = payload.replace("sub_", "").replace("_payload", "")
    
    if tariff_key not in ["standard", "premium"]:
        tariff_key = "standard"
    
    await activate_subscription(message.from_user.id, tariff_key)
    tariff = TARIFFS.get(tariff_key, TARIFFS["standard"])
    
    await message.answer(
        f"🎉 **Оплата прошла успешно!**\n\n"
        f"Тариф «{tariff['name']}» активирован на 30 дней!",
        parse_mode="Markdown"
    )

# ==========================================
# 🚀 ОСНОВНОЙ ОБРАБОТЧИК ССЫЛОК (С ПРЕДПРОСМОТРОМ)
# ==========================================
@dp.message(F.text.startswith(("http://", "https://")))
async def handle_link(message: types.Message):
    user_id = message.from_user.id
    url = message.text.strip()
    
    # Получаем информацию о видео
    info_msg = await message.answer("🔍 *Получаю информацию о видео...*", parse_mode="Markdown")
    video_info = await get_video_info(url)
    
    if not video_info:
        await info_msg.edit_text(
            "❌ **Не удалось получить информацию о видео.**\n\n"
            "Проверь ссылку или попробуй другую.",
            parse_mode="Markdown"
        )
        return
    
    size_mb = video_info["estimated_size_mb"]
    is_large = size_mb > 200
    
    preview_text = (
        "📹 **Информация о видео:**\n\n"
        f"📌 **Название:** {video_info['title']}\n"
        f"⏱️ **Длительность:** {video_info['duration_str']}\n"
        f"📱 **Платформа:** {video_info['platform'].capitalize()}\n"
        f"📦 **Примерный размер:** `{size_mb} МБ`\n"
    )
    
    if is_large:
        preview_text += (
            f"\n⚠️ **ВНИМАНИЕ!**\n"
            f"Видео весит **{size_mb} МБ**, что превышает лимит **200 МБ**.\n"
            f"Бот пока не поддерживает скачивание таких больших файлов.\n\n"
            f"💡 Попробуй видео поменьше или используй другой источник."
        )
        await info_msg.edit_text(preview_text, parse_mode="Markdown")
        return
    
    preview_text += (
        f"\n📌 **Лимит:** до 200 МБ\n"
        f"✅ Видео подходит по размеру!\n\n"
        f"🔄 Начинаю скачивание..."
    )
    
    await info_msg.edit_text(preview_text, parse_mode="Markdown")
    
    # --- ДАЛЬШЕ СТАНДАРТНОЕ СКАЧИВАНИЕ ---
    await get_or_create_user(user_id)
    
    platform = detect_platform(url)
    
    can_dl, error_msg = await can_download(user_id, platform)
    if not can_dl:
        await message.answer(
            error_msg + "\n\n💳 /tariff",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    status_msg = await message.answer("⏳ *Скачиваю...*", parse_mode="Markdown")
    
    file_path = f"temp_{user_id}_{message.message_id}.mp4"

    try:
        success = await download_media(url, file_path)
        if success:
            video_file = FSInputFile(file_path)
            await message.answer_video(
                video=video_file, 
                caption=f"✅ **Готово!**\n📱 {platform.capitalize()}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                reply_markup=get_main_keyboard()
            )
            await increment_downloads(user_id)
        else:
            await message.answer(
                "⚠️ **Не удалось скачать видео.**\n\n"
                "Проверь ссылку или попробуй другую.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
    finally:
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

# ==========================================
# 🚀 НЕИЗВЕСТНЫЕ СООБЩЕНИЯ
# ==========================================
@dp.message(F.text)
async def handle_unknown(message: types.Message):
    await message.answer(
        "❓ **Отправь ссылку на видео**\n\n"
        "🔗 TikTok, Instagram, YouTube, Pinterest, Twitter, Facebook",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# ==========================================
# 🚀 HTTP-СЕРВЕР ДЛЯ RENDER
# ==========================================
async def handle_healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    app.router.add_get("/health", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ HTTP-сервер запущен на порту {port}")

# ==========================================
# 🚀 ЗАПУСК
# ==========================================
async def main():
    await init_db()
    asyncio.create_task(start_dummy_server())
    print("🤖 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
