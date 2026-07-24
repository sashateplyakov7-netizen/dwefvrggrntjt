import asyncio
import os
import logging
import hashlib
import json
import re
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, FREE_DAILY_LIMIT, ADMIN_ID, TARIFFS, BOT_USERNAME, YOOMONEY_SHOP_ID, YOOMONEY_SECRET_KEY
from database import (
    init_db, get_or_create_user, increment_downloads, activate_subscription,
    get_admin_stats, grant_sub_by_admin, revoke_sub_by_admin, get_all_users,
    get_user_stats, get_user_tariff, can_download,
    generate_referral_link, process_referral, get_referral_info,
    get_paid_premium_count, is_free_premium_available,
    mark_free_premium_used, activate_free_premium,
    get_expiring_subs, get_expired_today,
    save_payment_label, get_pending_payment, clear_pending_payment,
    increment_paid_premium_count
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
# КЭШ ДЛЯ URL (ИСПРАВЛЕНИЕ BUTTON_DATA_INVALID)
# ==========================================
download_cache = {}

# ==========================================
# КЛАВИАТУРЫ
# ==========================================

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="show_tariffs")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton(text="🎉 Акция: Премиум БЕСПЛАТНО!", callback_data="show_promo")],
        [InlineKeyboardButton(text="📞 Связаться с админом", callback_data="contact_admin")]
    ])

def get_tariff_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Бесплатный", callback_data="tariff_free"),
            InlineKeyboardButton(text="⚡ Стандарт — 100 ₽", callback_data="tariff_standard")
        ],
        [InlineKeyboardButton(text="💎 Премиум — 300 ₽", callback_data="tariff_premium")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="main_menu")]
    ])

def get_payment_keyboard(tariff_key: str):
    """Клавиатура выбора способа оплаты"""
    keyboard = [
        [InlineKeyboardButton(text="⭐ Оплатить звёздами", callback_data=f"pay_stars_{tariff_key}")]
    ]
    
    # 🔥 КАРТА ДЛЯ ВСЕХ ТАРИФОВ
    keyboard.append([InlineKeyboardButton(text="💳 Оплатить картой", callback_data=f"pay_card_{tariff_key}")])
    
    # 🔥 БОНУС +3 ДНЯ ТОЛЬКО ДЛЯ ПРЕМИУМ
    if tariff_key == "premium":
        keyboard.append([InlineKeyboardButton(text="🎁 +3 дня БЕСПЛАТНО при оплате картой!", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton(text="🏠 Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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
        [InlineKeyboardButton(text="🎉 Акция: Премиум БЕСПЛАТНО!", callback_data="show_promo")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_quality_keyboard(qualities: list, url: str):
    """Клавиатура для выбора качества видео"""
    global download_cache
    
    buttons = []
    quality_names = {
        "sd": "📥 SD (480p)",
        "hd": "📥 HD (720p)",
        "fullhd": "📥 Full HD (1080p)"
    }
    
    # 🔥 ИСПОЛЬЗУЕМ ХЕШ ВМЕСТО URL (ЧТОБЫ НЕ БЫЛО BUTTON_DATA_INVALID)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    download_cache[url_hash] = url
    
    for q in qualities:
        if q in quality_names:
            buttons.append([InlineKeyboardButton(
                text=quality_names[q],
                callback_data=f"dl_{q}_{url_hash}"
            )])
    
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==========================================
# 🔥 ФУНКЦИЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ВИДЕО (С ОБХОДНЫМ ПУТЁМ)
# ==========================================
async def get_video_info(url: str) -> dict:
    """
    Получает информацию о видео без скачивания.
    Если extract_video_info не работает, использует обходной путь.
    """
    try:
        # Пытаемся получить информацию через extract_video_info
        info = await asyncio.to_thread(extract_video_info, url)
        
        if info and info.get("extractor") != "unknown":
            duration_sec = info.get("duration", 0)
            
            # Определяем размер для разных качеств
            estimated_size_mb = {
                "sd": round((duration_sec * 2) / 8, 1),      # 2 Мбит/с
                "hd": round((duration_sec * 5) / 8, 1),      # 5 Мбит/с
                "fullhd": round((duration_sec * 10) / 8, 1)  # 10 Мбит/с
            }
            
            return {
                "title": info.get("title", "Неизвестно")[:50],
                "duration": duration_sec,
                "duration_str": f"{duration_sec // 60}:{duration_sec % 60:02d}",
                "estimated_size_mb": estimated_size_mb,
                "platform": info.get("platform", "unknown"),
                "thumbnail": info.get("thumbnail"),
                "extractor": info.get("extractor", "unknown")
            }
        
        # 🔥 ОБХОДНОЙ ПУТЬ: определяем платформу по URL
        platform = detect_platform(url)
        
        # Пытаемся извлечь ID видео из URL
        video_id = None
        if "youtube.com" in url or "youtu.be" in url:
            match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", url)
            if match:
                video_id = match.group(1)
                title = f"YouTube видео {video_id}"
            else:
                title = "YouTube видео"
        elif "tiktok.com" in url:
            match = re.search(r"/video/(\d+)", url)
            if match:
                video_id = match.group(1)
                title = f"TikTok видео {video_id}"
            else:
                title = "TikTok видео"
        elif "instagram.com" in url:
            match = re.search(r"/reel/([^/?]+)", url)
            if match:
                video_id = match.group(1)
                title = f"Instagram Reel {video_id}"
            else:
                title = "Instagram видео"
        elif "pinterest.com" in url:
            title = "Pinterest видео"
        elif "twitter.com" in url or "x.com" in url:
            title = "Twitter/X видео"
        elif "facebook.com" in url:
            title = "Facebook видео"
        else:
            title = "Видео"
        
        # Предполагаем длительность 60 секунд (если не можем определить)
        duration_sec = 60
        estimated_size_mb = {
            "sd": round((duration_sec * 2) / 8, 1),
            "hd": round((duration_sec * 5) / 8, 1),
            "fullhd": round((duration_sec * 10) / 8, 1)
        }
        
        return {
            "title": title[:50],
            "duration": duration_sec,
            "duration_str": f"{duration_sec // 60}:{duration_sec % 60:02d}",
            "estimated_size_mb": estimated_size_mb,
            "platform": platform,
            "thumbnail": None,
            "extractor": "fallback"
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
        "   • 3 скачивания в день — хватит, чтобы понять, что бот 🔥\n"
        "   • TikTok, Instagram, Pinterest\n"
        "   • SD качество (480p) — для быстрых просмотров\n\n"
        "⚡ **Стандарт** — 100 ₽/мес\n"
        "   • 30 скачиваний в день — для тех, кто не хочет ждать\n"
        "   • Все основные платформы\n"
        "   • HD качество (720p) — чётко и ясно\n\n"
        "💎 **Премиум** — 300 ₽/мес\n"
        "   • ♾️ Безлимит — качай сколько влезет!\n"
        "   • Все платформы — даже те, о которых ты не знал\n"
        "   • Full HD (1080p) — сочные детали\n"
        "   • Умный кэш — видео вылетает мгновенно\n"
        "   • Приоритетная обработка — ты король, все ждут тебя\n\n"
        "🎁 **Акция:** каждый 3-й Премиум — БЕСПЛАТНО! Не веришь? Проверь!",
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
    premium_count = await get_paid_premium_count(user_id)
    
    if stats:
        text = (
            "📊 **Твоя статистика:**\n\n"
            f"📥 Скачиваний сегодня: {stats['downloads_today']} — не слабо!\n"
            f"📅 Всего скачиваний: {stats['total_downloads']} — гордись собой\n"
            f"💎 Тариф: **{tariff_info['name']}** — ты на коне!\n"
            f"📊 Статус: {'🟢 Активна' if stats['is_subscribed'] == 1 else '🔴 Не активна'}\n"
            f"📅 Действует до: {stats['sub_end_date'] or 'Нет'}\n\n"
            f"📱 Доступно платформ: {len(tariff_info['platforms']) if tariff_info['platforms'] != ['all'] else 'Все'}\n"
            f"📊 Лимит в день: {tariff_info['daily_limit'] if tariff_info['daily_limit'] != 9999 else '∞'}\n\n"
            f"🎁 **Рефералы:**\n"
            f"• Приглашено: {referral_info['count']} друзей — ты популярен!\n"
            f"• Награда за 1 друга: {'✅ Получен' if referral_info['standard_used'] else '❌ Не получен'}\n"
            f"• Награда за 3 друзей: {'✅ Получен' if referral_info['premium_used'] else '❌ Не получен'}\n\n"
            f"🎉 **Акция:**\n"
            f"• Куплено Премиум: {premium_count} раз(а)\n"
            f"• До бесплатного месяца: {3 - (premium_count % 3) if premium_count % 3 != 0 else 3} Премиум(а) — осталось чуть-чуть!"
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
        "/promo — Информация об акции\n"
        "/admin — Панель управления (админ)\n"
        "/help — Эта справка\n\n"
        "🔗 Просто отправь ссылку на видео — я скачаю его!\n\n"
        "🎁 **Реферальная программа:**\n"
        "• Пригласи 1 друга → получи Стандарт на месяц\n"
        "• Пригласи 3 друзей → получи Премиум на месяц\n\n"
        "🎉 **Акция:**\n"
        "• Каждый 3-й Премиум — БЕСПЛАТНО!\n\n"
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
# 🚀 КОМАНДА /PROMO - ИНФОРМАЦИЯ ОБ АКЦИИ
# ==========================================
@dp.message(Command("promo"))
async def cmd_promo(message: types.Message):
    user_id = message.from_user.id
    count = await get_paid_premium_count(user_id)
    
    if count == 0:
        text = (
            "🎁 **Акция: каждый 3-й Премиум — БЕСПЛАТНО!**\n\n"
            "Ты ещё не покупал Премиум.\n"
            "Купи 2 раза, а 3-й получи в подарок! 🎉\n\n"
            "💎 /tariff — выбрать тариф"
        )
    else:
        next_free = 3 - (count % 3)
        if next_free == 0:
            next_free = 3
        
        text = (
            "🎁 **Акция: каждый 3-й Премиум — БЕСПЛАТНО!**\n\n"
            f"📊 Ты купил Премиум: **{count}** раз(а)\n"
            f"🎯 Осталось оплатить: **{next_free}** Премиум(а) до бесплатного месяца!\n\n"
            f"💎 /tariff — выбрать тариф"
        )
    
    await message.answer(text, parse_mode="Markdown")

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
        "🎉 **Акция:** каждый 3-й Премиум — БЕСПЛАТНО!\n\n"
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
# 🚀 КНОПКА АКЦИИ
# ==========================================
@dp.callback_query(F.data == "show_promo")
async def show_promo_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    count = await get_paid_premium_count(user_id)
    
    if count == 0:
        text = (
            "🎁 **Акция: каждый 3-й Премиум — БЕСПЛАТНО!**\n\n"
            "Ты ещё не покупал Премиум.\n"
            "Купи 2 раза, а 3-й получи в подарок! 🎉\n\n"
            "💎 Нажми «Выбрать тариф» чтобы начать."
        )
    else:
        next_free = 3 - (count % 3)
        if next_free == 0:
            next_free = 3
        
        text = (
            "🎁 **Акция: каждый 3-й Премиум — БЕСПЛАТНО!**\n\n"
            f"📊 Ты купил Премиум: **{count}** раз(а)\n"
            f"🎯 Осталось оплатить: **{next_free}** Премиум(а) до бесплатного месяца!\n\n"
            f"💎 Нажми «Выбрать тариф» чтобы купить."
        )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
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
        "🎁 Пригласи друга → получи подписку!\n"
        "🎉 Каждый 3-й Премиум — БЕСПЛАТНО!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "show_tariffs")
async def show_tariffs(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💎 **Тарифы**\n\n"
        "📱 **Бесплатный** — 0 ₽\n"
        "   • 3 скачивания в день — хватит, чтобы понять, что бот 🔥\n"
        "   • TikTok, Instagram, Pinterest\n"
        "   • SD качество (480p)\n\n"
        "⚡ **Стандарт** — 100 ₽/мес\n"
        "   • 30 скачиваний в день — для тех, кто не хочет ждать\n"
        "   • Все основные платформы\n"
        "   • HD качество (720p)\n\n"
        "💎 **Премиум** — 300 ₽/мес\n"
        "   • ♾️ Безлимит — качай сколько влезет!\n"
        "   • Все платформы\n"
        "   • Full HD (1080p) — сочные детали\n"
        "   • Умный кэш, приоритетная обработка — ты король!\n\n"
        "🎁 **Акция:** каждый 3-й Премиум — БЕСПЛАТНО!",
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
    premium_count = await get_paid_premium_count(user_id)
    
    if stats:
        text = (
            "📊 **Твоя статистика**\n\n"
            f"📥 Сегодня: {stats['downloads_today']} — не слабо!\n"
            f"📅 Всего: {stats['total_downloads']} — гордись собой\n"
            f"💎 Тариф: **{tariff_info['name']}** — ты на коне!\n"
            f"📊 Статус: {'🟢 Активна' if stats['is_subscribed'] == 1 else '🔴 Не активна'}\n"
            f"📅 Действует до: {stats['sub_end_date'] or 'Нет'}\n\n"
            f"🎁 Приглашено: {referral_info['count']} друзей — ты популярен!\n"
            f"🎉 Куплено Премиум: {premium_count} раз(а)"
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
            "3 скачивания в день — хватит, чтобы понять, что бот 🔥\n"
            "TikTok, Instagram, Pinterest\n\n"
            "🎁 **Акция:** каждый 3-й Премиум — БЕСПЛАТНО!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return
    
    tariff = TARIFFS.get(tariff_key)
    if not tariff:
        await callback.answer("❌ Тариф не найден")
        return
    
    # Показываем выбор способа оплаты
    await callback.message.edit_text(
        f"💎 **Тариф «{tariff['name']}»**\n\n"
        f"💰 Цена: {tariff['price']} ₽\n"
        f"📊 Лимит: {tariff['daily_limit']} скачиваний/день\n"
        f"📱 Платформы: {', '.join(tariff['platforms']) if tariff['platforms'] != ['all'] else 'Все'}\n\n"
        f"🎁 **Акция:** каждый 3-й Премиум — БЕСПЛАТНО!\n"
        f"{'🎁 **Бонус:** +3 дня БЕСПЛАТНО при оплате картой!' if tariff_key == 'premium' else ''}",
        parse_mode="Markdown",
        reply_markup=get_payment_keyboard(tariff_key)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_stars_"))
async def process_pay_stars(callback: types.CallbackQuery):
    tariff_key = callback.data.replace("pay_stars_", "")
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

@dp.callback_query(F.data.startswith("pay_card_"))
async def process_pay_card(callback: types.CallbackQuery):
    tariff_key = callback.data.replace("pay_card_", "")
    user_id = callback.from_user.id
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден")
        return
    
    # Генерируем ссылку для оплаты через ЮMoney
    payment_label = f"card_{tariff_key}_{user_id}_{int(datetime.now().timestamp())}"
    await save_payment_label(user_id, payment_label, tariff_key)
    
    # Используем переменную из config
    payment_link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_SHOP_ID}&quickpay-form=shop&targets=Подписка+{tariff['name']}&paymentType=SB&sum={tariff['price']}&label={payment_label}"
    
    bonus_text = "\n\n🎁 **Бонус:** +3 дня к подписке БЕСПЛАТНО! 😈" if tariff_key == "premium" else ""
    
    await callback.message.edit_text(
        f"💳 **Оплата через карту (ЮMoney)**\n\n"
        f"💎 Тариф: **{tariff['name']}**\n"
        f"💰 Сумма: **{tariff['price']} ₽**\n"
        f"{bonus_text}\n\n"
        f"🔗 **Ссылка для оплаты:**\n"
        f"`{payment_link}`\n\n"
        f"📌 После оплаты подписка активируется автоматически!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Перейти к оплате", url=payment_link)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
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
    
    user_id = message.from_user.id
    
    # Увеличиваем счётчик оплаченных Премиумов
    if tariff_key == "premium":
        await increment_paid_premium_count(user_id)
    
    # 🔥 ПРОВЕРЯЕМ АКЦИЮ ДЛЯ ПРЕМИУМА
    if tariff_key == "premium":
        # Проверяем, есть ли право на бесплатный Премиум
        if await is_free_premium_available(user_id):
            # Отмечаем, что использовали бесплатный
            await mark_free_premium_used(user_id)
            
            # Даём следующий месяц бесплатно (БЕЗ ОПЛАТЫ)
            await activate_free_premium(user_id)
            
            await message.answer(
                f"🎉 **ПОЗДРАВЛЯЮ!**\n\n"
                f"Ты оплатил **2 Премиума**!\n"
                f"По акции ты получаешь **3-й месяц БЕСПЛАТНО**! 🎁\n\n"
                f"💎 Тариф «Премиум» активирован на 30 дней!\n"
                f"💰 Сумма к оплате: **0 ₽**",
                parse_mode="Markdown"
            )
            
            # Отправляем уведомление админу
            await bot.send_message(
                ADMIN_ID,
                f"🎁 **АКЦИЯ АКТИВИРОВАНА!**\n\n"
                f"👤 Пользователь `{user_id}` получил бесплатный Премиум!\n"
                f"📊 Это его 3-й Премиум (2 оплаченных + 1 бесплатный).",
                parse_mode="Markdown"
            )
            return
    
    # Обычная активация
    await activate_subscription(user_id, tariff_key)
    tariff = TARIFFS.get(tariff_key, TARIFFS["standard"])
    
    # Показываем прогресс акции
    if tariff_key == "premium":
        count = await get_paid_premium_count(user_id)
        next_free = 3 - (count % 3)
        if next_free == 0:
            next_free = 3
        
        await message.answer(
            f"🎉 **Оплата прошла успешно!**\n\n"
            f"💎 Тариф «{tariff['name']}» активирован на 30 дней!\n\n"
            f"🎁 **Акция:** каждый 3-й Премиум — БЕСПЛАТНО!\n"
            f"📊 Осталось оплатить: **{next_free}** Премиум(а) до бесплатного месяца!",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"🎉 **Оплата прошла успешно!**\n\n"
            f"📊 Тариф «{tariff['name']}» активирован на 30 дней!\n\n"
            f"💡 Переходи на Премиум — каждый 3-й месяц БЕСПЛАТНО!",
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
    
    # Получаем тариф пользователя
    tariff_key = await get_user_tariff(user_id)
    tariff_info = TARIFFS.get(tariff_key, TARIFFS["free"])
    
    # Определяем доступные качества в зависимости от тарифа
    available_qualities = ["sd"]  # SD доступно всем
    
    if tariff_key in ["standard", "premium"]:
        available_qualities.append("hd")
    
    if tariff_key == "premium":
        available_qualities.append("fullhd")
    
    # Формируем информацию о размерах
    sizes_text = ""
    for q in available_qualities:
        size_mb = video_info["estimated_size_mb"].get(q, 0)
        quality_names = {"sd": "SD (480p)", "hd": "HD (720p)", "fullhd": "Full HD (1080p)"}
        sizes_text += f"   • {quality_names.get(q, q)}: ~{size_mb} МБ\n"
    
    preview_text = (
        "📹 **Информация о видео:**\n\n"
        f"📌 **Название:** {video_info['title']}\n"
        f"⏱️ **Длительность:** {video_info['duration_str']}\n"
        f"📱 **Платформа:** {video_info['platform'].capitalize()}\n"
        f"📦 **Размер файла:**\n{sizes_text}\n"
        f"💎 **Ваш тариф:** {tariff_info['name']}\n\n"
        f"⬇️ **Выберите качество для скачивания:**"
    )
    
    await info_msg.edit_text(
        preview_text,
        parse_mode="Markdown",
        reply_markup=get_quality_keyboard(available_qualities, url)
    )

# ==========================================
# 🚀 ОБРАБОТЧИК ВЫБОРА КАЧЕСТВА
# ==========================================
@dp.callback_query(F.data.startswith("dl_"))
async def process_download_quality(callback: types.CallbackQuery):
    global download_cache
    
    user_id = callback.from_user.id
    data = callback.data.replace("dl_", "")
    
    # Парсим качество и хеш
    parts = data.split("_", 1)
    if len(parts) < 2:
        await callback.answer("❌ Ошибка формата")
        return
    
    quality = parts[0]
    url_hash = parts[1]
    
    # Восстанавливаем URL из кэша
    url = download_cache.get(url_hash)
    if not url:
        await callback.message.answer(
            "❌ Ссылка устарела. Отправь видео заново.",
            parse_mode="Markdown"
        )
        return
    
    await callback.answer(f"⏳ Начинаю скачивание в {quality.upper()}...")
    
    # Получаем тариф пользователя
    tariff_key = await get_user_tariff(user_id)
    tariff_info = TARIFFS.get(tariff_key, TARIFFS["free"])
    
    # Проверяем доступность качества
    available = ["sd"]
    if tariff_key in ["standard", "premium"]:
        available.append("hd")
    if tariff_key == "premium":
        available.append("fullhd")
    
    if quality not in available:
        await callback.message.answer(
            f"❌ Качество {quality.upper()} недоступно для твоего тарифа.\n"
            f"Доступно: {', '.join(available).upper()}",
            parse_mode="Markdown"
        )
        return
    
    # Проверяем лимиты и платформу
    platform = detect_platform(url)
    can_dl, error_msg = await can_download(user_id, platform)
    if not can_dl:
        await callback.message.answer(
            error_msg + "\n\n💳 /tariff",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    status_msg = await callback.message.answer("⏳ *Скачиваю...*", parse_mode="Markdown")
    
    file_path = f"temp_{user_id}_{int(datetime.now().timestamp())}.mp4"
    
    try:
        success = await download_media(url, file_path, quality)
        if success:
            video_file = FSInputFile(file_path)
            await callback.message.answer_video(
                video=video_file,
                caption=f"✅ **Готово!**\n📱 {platform.capitalize()}\n🎬 Качество: {quality.upper()}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                reply_markup=get_main_keyboard()
            )
            await increment_downloads(user_id)
        else:
            await callback.message.answer(
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
# 💳 WEBHOOK ДЛЯ ЮMONEY
# ==========================================
async def yoomoney_webhook(request):
    """
    Обработчик webhook от ЮMoney.
    Принимает уведомления об успешных платежах.
    """
    try:
        data = await request.post()
        
        # Проверяем подпись
        notification_type = data.get('notification_type')
        operation_id = data.get('operation_id')
        amount = data.get('amount')
        currency = data.get('currency')
        datetime_str = data.get('datetime')
        sender = data.get('sender')
        codepro = data.get('codepro')
        label = data.get('label')
        sha1_hash = data.get('sha1_hash')
        
        # Проверяем хеш
        check_string = f"{notification_type}&{operation_id}&{amount}&{currency}&{datetime_str}&{sender}&{codepro}&{YOOMONEY_SECRET_KEY}&{label}"
        check_hash = hashlib.sha1(check_string.encode()).hexdigest()
        
        if check_hash != sha1_hash:
            return web.Response(text="Invalid signature", status=400)
        
        # Парсим label: card_{tariff_key}_{user_id}_{timestamp}
        parts = label.split("_")
        if len(parts) >= 3 and parts[0] == "card":
            tariff_key = parts[1]
            user_id = int(parts[2])
            
            # Если Премиум — увеличиваем счётчик
            if tariff_key == "premium":
                await increment_paid_premium_count(user_id)
                
                # Проверяем акцию
                if await is_free_premium_available(user_id):
                    await mark_free_premium_used(user_id)
                    await activate_free_premium(user_id)
                    
                    await bot.send_message(
                        user_id,
                        f"🎉 **ПОЗДРАВЛЯЮ!**\n\n"
                        f"Ты оплатил 2 Премиума через карту!\n"
                        f"По акции ты получаешь **3-й месяц БЕСПЛАТНО**! 🎁\n\n"
                        f"💎 Тариф «Премиум» активирован на 30 дней!\n"
                        f"💰 Сумма к оплате: **0 ₽**",
                        parse_mode="Markdown"
                    )
                    
                    await bot.send_message(
                        ADMIN_ID,
                        f"🎁 **АКЦИЯ АКТИВИРОВАНА!**\n\n"
                        f"👤 Пользователь `{user_id}` получил бесплатный Премиум через карту!\n"
                        f"📊 Это его 3-й Премиум (2 оплаченных + 1 бесплатный).",
                        parse_mode="Markdown"
                    )
                    
                    await clear_pending_payment(user_id)
                    return web.Response(text="OK", status=200)
            
            # Обычная активация
            await activate_subscription(user_id, tariff_key)
            await clear_pending_payment(user_id)
            
            tariff = TARIFFS.get(tariff_key, TARIFFS["standard"])
            
            # Отправляем уведомление пользователю
            bonus_text = "\n🎁 Бонус: +3 дня к подписке!" if tariff_key == "premium" else ""
            
            await bot.send_message(
                user_id,
                f"🎉 **Оплата через карту прошла успешно!**\n\n"
                f"💎 Тариф «{tariff['name']}» активирован на 30 дней!{bonus_text}",
                parse_mode="Markdown"
            )
            
            # Отправляем уведомление админу
            await bot.send_message(
                ADMIN_ID,
                f"💳 **Оплата через ЮMoney!**\n\n"
                f"👤 Пользователь: `{user_id}`\n"
                f"💎 Тариф: {tariff_key}\n"
                f"💰 Сумма: {amount} ₽",
                parse_mode="Markdown"
            )
        
        return web.Response(text="OK", status=200)
        
    except Exception as e:
        print(f"❌ Ошибка в webhook: {e}")
        return web.Response(text="Error", status=500)

# ==========================================
# 🔔 ФОНОВЫЙ ТАСК ДЛЯ ПРОВЕРКИ ПОДПИСОК (ПУШИ)
# ==========================================
async def check_subscriptions():
    """
    Проверяет подписки и отправляет дружелюбные уведомления.
    Запускается каждые 6 часов.
    """
    while True:
        try:
            # 🔔 За 3 дня до окончания
            expiring_soon = await get_expiring_subs(3)
            for user in expiring_soon:
                try:
                    tariff = await get_user_tariff(user["user_id"])
                    
                    if tariff == "premium":
                        msg = (
                            f"👋 Привет!\n\n"
                            f"Твой Премиум заканчивается через **3 дня**.\n"
                            f"📅 Последний день: {user['sub_end_date']}\n\n"
                            f"Если хочешь сохранить безлимит — продли подписку:\n"
                            f"/tariff"
                        )
                    else:
                        msg = (
                            f"👋 Привет!\n\n"
                            f"Твой Стандарт заканчивается через **3 дня**.\n"
                            f"📅 Последний день: {user['sub_end_date']}\n\n"
                            f"Если хочешь продолжить скачивать без ограничений — продли подписку:\n"
                            f"/tariff"
                        )
                    
                    await bot.send_message(user["user_id"], msg, parse_mode="Markdown")
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            
            # 🔔 За 1 день до окончания
            expiring_soon = await get_expiring_subs(1)
            for user in expiring_soon:
                try:
                    tariff = await get_user_tariff(user["user_id"])
                    
                    if tariff == "premium":
                        msg = (
                            f"⏰ Привет! Напоминаю, что завтра заканчивается Премиум.\n\n"
                            f"📅 Последний день: {user['sub_end_date']}\n\n"
                            f"Чтобы сохранить безлимит — продли через /tariff.\n"
                            f"Если нет — перейдёшь на Бесплатный тариф (3 видео в день)."
                        )
                    else:
                        msg = (
                            f"⏰ Привет! Напоминаю, что завтра заканчивается Стандарт.\n\n"
                            f"📅 Последний день: {user['sub_end_date']}\n\n"
                            f"Чтобы сохранить 30 скачиваний в день — продли через /tariff.\n"
                            f"Если нет — перейдёшь на Бесплатный тариф (3 видео в день)."
                        )
                    
                    await bot.send_message(user["user_id"], msg, parse_mode="Markdown")
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            
            # 🔔 В день окончания
            expired_today = await get_expired_today()
            for user in expired_today:
                try:
                    tariff = await get_user_tariff(user["user_id"])
                    
                    if tariff == "premium":
                        msg = (
                            f"👋 Привет! Сегодня последний день Премиума.\n\n"
                            f"📅 Заканчивается сегодня: {user['sub_end_date']}\n\n"
                            f"Чтобы остаться с безлимитом — продли через /tariff.\n"
                            f"Если нет — перейдёшь на Бесплатный тариф (3 видео в день)."
                        )
                    else:
                        msg = (
                            f"👋 Привет! Сегодня последний день Стандарта.\n\n"
                            f"📅 Заканчивается сегодня: {user['sub_end_date']}\n\n"
                            f"Чтобы остаться с 30 скачиваниями в день — продли через /tariff.\n"
                            f"Если нет — перейдёшь на Бесплатный тариф (3 видео в день)."
                        )
                    
                    await bot.send_message(user["user_id"], msg, parse_mode="Markdown")
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            
            await asyncio.sleep(21600)  # 6 часов
            
        except Exception as e:
            print(f"❌ Ошибка в check_subscriptions: {e}")
            await asyncio.sleep(3600)

# ==========================================
# 🚀 HTTP-СЕРВЕР ДЛЯ RENDER
# ==========================================
async def handle_healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    app.router.add_get("/health", handle_healthcheck)
    app.router.add_post("/yoomoney-webhook", yoomoney_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ HTTP-сервер запущен на порту {port}")
    print(f"✅ Webhook для ЮMoney: /yoomoney-webhook")

# ==========================================
# 🚀 ЗАПУСК
# ==========================================
async def main():
    await init_db()
    asyncio.create_task(start_dummy_server())
    asyncio.create_task(check_subscriptions())
    print("🤖 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
