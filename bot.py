import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, FREE_DAILY_LIMIT, SUB_PRICE, ADMIN_ID
from database import (
    init_db, get_or_create_user, increment_downloads, activate_subscription,
    get_admin_stats, grant_sub_by_admin, revoke_sub_by_admin, get_all_users,
    get_user_stats
)
from downloader import download_media

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
    waiting_for_answer = State()  # ✅ НОВОЕ: для ответа пользователю

# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def get_pay_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Купить Безлимит — {SUB_PRICE} ₽ / мес", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
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
        [InlineKeyboardButton(text="💳 Купить Безлимит", callback_data="buy_sub")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="💳 Купить Безлимит", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📞 Связаться с админом", callback_data="contact_admin")]
    ])

# ==========================================
# КОМАНДЫ
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await get_or_create_user(message.from_user.id)
    await message.answer(
        "👋 **Салют! Я качаю видео без водяных знаков** из TikTok, Reels, Shorts и Pinterest!\n\n"
        "🔗 Просто отправь мне ссылку на видео.\n"
        f"📊 Твой лимит: {FREE_DAILY_LIMIT} бесплатных скачиваний в день.\n\n"
        "ℹ️ *Поддерживаемые платформы:* TikTok, Instagram, YouTube, Pinterest, Twitter/X, Facebook",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 **Главное меню**\n\n"
        "Просто отправь мне ссылку на видео — я скачаю его без водяных знаков!\n\n"
        f"📊 Твой лимит: {FREE_DAILY_LIMIT} скачиваний в день.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "my_stats")
async def my_stats_callback(callback: types.CallbackQuery):
    stats = await get_user_stats(callback.from_user.id)
    if stats:
        text = (
            "📊 **Твоя статистика:**\n\n"
            f"📥 Скачиваний сегодня: {stats['downloads_today']}\n"
            f"📅 Всего скачиваний: {stats['total_downloads']}\n"
            f"💎 Статус: {'🟢 Активна' if stats['is_subscribed'] else '🔴 Не активна'}\n"
            f"📅 Дата активации: {stats['sub_start'] or 'Нет'}\n"
            f"📅 Дата окончания: {stats['sub_end'] or 'Нет'}"
        )
    else:
        text = "⚠️ Не удалось получить данные."
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_user_stats_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "contact_admin")
async def contact_admin_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 **Напиши своё сообщение администратору.**\n\n"
        "Я передам его создателю бота, и он ответит тебе как можно скорее."
    )
    await state.set_state(AdminState.waiting_for_answer)
    await callback.answer()

@dp.message(AdminState.waiting_for_answer)
async def process_user_message_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.full_name or "Пользователь"
    user_link = f"tg://user?id={user_id}"
    
    text = (
        f"💬 **Новое сообщение от пользователя**\n\n"
        f"👤 **Имя:** {user_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"🔗 [Ссылка на профиль]({user_link})\n\n"
        f"📝 **Текст:**\n{message.text}"
    )
    
    # Отправляем админу
    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=text, parse_mode="Markdown")
    elif message.video:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=text, parse_mode="Markdown")
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=text, parse_mode="Markdown")
    else:
        await bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    
    await message.answer(
        "✅ **Твоё сообщение отправлено администратору!**\n\n"
        "Он ответит тебе в ближайшее время."
    )
    await state.clear()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав для выполнения этой команды.")
        return
    
    await state.clear()
    await message.answer(
        "👑 **Панель управления создателя**\n\nВыбери нужное действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

# ==========================================
# АДМИН-ОБРАБОТЧИКИ
# ==========================================
@dp.callback_query(F.data.startswith("admin_"))
async def process_admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    action = callback.data.split("_")[1]

    if action == "stats":
        stats = await get_admin_stats()
        text = (
            "📈 **Актуальная статистика:**\n\n"
            f"👥 Всего юзеров: **{stats['total_users']}**\n"
            f"💎 Активных подписок: **{stats['active_subs']}**\n"
            f"📥 Скачиваний сегодня: **{stats['total_downloads']}**\n"
            f"🕐 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

    elif action == "broadcast":
        await callback.message.answer("📢 Отправь сообщение (текст, фото или видео), которое нужно разослать всем юзерам:")
        await state.set_state(AdminState.waiting_for_broadcast_msg)

    elif action == "give":
        await callback.message.answer("🎁 Отправь ID пользователя, которому нужно выдать безлимит:")
        await state.set_state(AdminState.waiting_for_give_sub_id)

    elif action == "revoke":
        await callback.message.answer("❌ Отправь ID пользователя, у которого нужно забрать безлимит:")
        await state.set_state(AdminState.waiting_for_revoke_sub_id)

    elif action == "answer":
        await callback.message.answer(
            "💬 **Ответить пользователю**\n\n"
            "Напиши: `user_id|сообщение`\n"
            "Например: `123456789|Привет, видео скачается через пару минут.`"
        )
        await state.set_state(AdminState.waiting_for_answer_to_user)

    elif action == "export":
        await export_database(callback.message)
        return

    elif action == "cancel":
        await state.clear()
        await callback.message.edit_text("🔄 Действие отменено.", reply_markup=get_admin_keyboard())
        
    await callback.answer()

@dp.message(AdminState.waiting_for_answer_to_user)
async def process_answer_to_user(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text
    if "|" not in text:
        await message.answer("⚠️ Неправильный формат. Используй: `user_id|сообщение`")
        return
    
    try:
        user_id_str, answer_text = text.split("|", 1)
        user_id = int(user_id_str.strip())
        answer_text = answer_text.strip()
        
        if not answer_text:
            await message.answer("❌ Текст сообщения не может быть пустым.")
            return
        
        await bot.send_message(
            user_id,
            f"💬 **Ответ от администратора:**\n\n{answer_text}"
        )
        await message.answer(f"✅ Ответ отправлен пользователю `{user_id}`")
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом.")
    
    await state.clear()

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
            
    await message.answer(f"✅ Рассылка завершена!\nУспешно доставлено: {success_count} из {len(users)}")
    await state.clear()

@dp.message(AdminState.waiting_for_give_sub_id)
async def process_give_sub(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    if not message.text.isdigit():
        await message.answer("⚠️ ID должен состоять только из цифр. Попробуй еще раз или напиши /admin для отмены.")
        return
        
    target_id = int(message.text)
    await grant_sub_by_admin(target_id)
    await message.answer(f"✅ Пользователю `{target_id}` успешно выдан безлимит!", parse_mode="Markdown")
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
    await message.answer(f"❌ У пользователя `{target_id}` забрали безлимит.", parse_mode="Markdown")
    await state.clear()

# ==========================================
# ЭКСПОРТ БАЗЫ ДАННЫХ
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
                caption=f"📦 **Экспорт базы данных**\n\nВсего пользователей: {len(users)}"
            )
        
        os.remove(filename)
        
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при экспорте: {str(e)}")

# ==========================================
# ОПЛАТА
# ==========================================
@dp.callback_query(F.data == "buy_sub")
async def process_buy_sub(callback: types.CallbackQuery):
    stars_amount = int(SUB_PRICE / 2)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Безлимитная подписка",
        description="Скачивание любых видео без ограничений и лимитов на 30 дней.",
        payload="sub_monthly_payload",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=stars_amount)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    await activate_subscription(message.from_user.id)
    await message.answer(
        "🎉 **Оплата прошла успешно!**\n\n"
        "Подписка активирована. Теперь у тебя безлимитный доступ!"
    )

# ==========================================
# ОСНОВНОЙ ОБРАБОТЧИК ССЫЛОК
# ==========================================
@dp.message(F.text.startswith(("http://", "https://")))
async def handle_link(message: types.Message):
    user_id = message.from_user.id
    user = await get_or_create_user(user_id)

    if not user["is_subscribed"] and user["downloads_today"] >= FREE_DAILY_LIMIT:
        await message.answer(
            f"❌ **Лимит на сегодня исчерпан ({FREE_DAILY_LIMIT}/{FREE_DAILY_LIMIT}).**\n\n"
            "Приходи завтра или включи безлимит всего за 100 рублей!",
            reply_markup=get_pay_keyboard(),
            parse_mode="Markdown"
        )
        return

    status_msg = await message.answer("⏳ *Скачиваю медиа... Подожди пару секунд.*", parse_mode="Markdown")
    
    file_path = f"temp_{user_id}_{message.message_id}.mp4"

    try:
        success = await download_media(message.text, file_path)
        if success:
            video_file = FSInputFile(file_path)
            await message.answer_video(
                video=video_file, 
                caption="✅ **Вот твоё видео без водяных знаков!**\n\n"
                       "🎬 Скачано через бота\n"
                       "📅 " + datetime.now().strftime("%d.%m.%Y %H:%M"),
                reply_markup=get_main_keyboard()
            )
            if not user["is_subscribed"]:
                await increment_downloads(user_id)
        else:
            await message.answer(
                "⚠️ **Не удалось скачать видео.**\n\n"
                "Проверь ссылку или попробуй другую.\n\n"
                "Поддерживаемые платформы:\n"
                "• TikTok\n"
                "• Instagram (Reels, видео)\n"
                "• YouTube (Shorts, видео)\n"
                "• Pinterest (видео)\n"
                "• Twitter/X\n"
                "• Facebook",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
    finally:
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

# ==========================================
# ОБРАБОТКА НЕИЗВЕСТНЫХ СООБЩЕНИЙ
# ==========================================
@dp.message(F.text)
async def handle_unknown(message: types.Message):
    await message.answer(
        "❓ **Я не понял, что ты хочешь.**\n\n"
        "🔗 Просто отправь мне ссылку на видео из TikTok, Instagram, YouTube или Pinterest.\n"
        "💳 Или используй кнопки ниже.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# ==========================================
# HTTP-СЕРВЕР ДЛЯ RENDER
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
# ЗАПУСК
# ==========================================
async def main():
    await init_db()
    await start_dummy_server()
    print("🤖 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
