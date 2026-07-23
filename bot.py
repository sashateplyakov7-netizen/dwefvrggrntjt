import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, FREE_DAILY_LIMIT, SUB_PRICE, ADMIN_ID
from database import (
    init_db, get_or_create_user, increment_downloads, activate_subscription,
    get_admin_stats, grant_sub_by_admin, revoke_sub_by_admin, get_all_users
)
from downloader import download_media

# Настраиваем сессию с увеличенным таймаутом (5 минут = 300 секунд)
session = AiohttpSession(timeout=300)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Состояния для админки
class AdminState(StatesGroup):
    waiting_for_broadcast_msg = State()
    waiting_for_give_sub_id = State()
    waiting_for_revoke_sub_id = State()

# Кнопка для оплаты
def get_pay_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Купить Безлимит — {SUB_PRICE} ₽ / мес", callback_data="buy_sub")]
    ])
    return kb

# Клавиатура админ-панели
def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(text="🎁 Выдать сабку", callback_data="admin_give_sub"),
            InlineKeyboardButton(text="❌ Забрать сабку", callback_data="admin_revoke_sub")
        ],
        [InlineKeyboardButton(text="Сбросить действие", callback_data="admin_cancel")]
    ])

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await get_or_create_user(message.from_user.id)
    await message.answer(
        "👋 **Салют! Я качаю видео без водяных знаков** из TikTok, Reels, Shorts и Pinterest!\n\n"
        "🔗 Просто отправь мне ссылку на видео.\n"
        f"📊 Твой лимит: {FREE_DAILY_LIMIT} бесплатное скачивание в день.",
        parse_mode="Markdown"
    )

# === АДМИН-ПАНЕЛЬ И КОМАНДЫ ===

@dp.message(F.text == "/admin")
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    await message.answer(
        "👑 **Панель управления создателя**\n\nВыбери нужное действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

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
            f"📥 Скачиваний сегодня: **{stats['total_downloads']}**"
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

    elif action == "cancel":
        await state.clear()
        await callback.message.edit_text("Действие отменено.", reply_markup=get_admin_keyboard())
        
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

# === ОПЛАТА И СКАЧИВАНИЕ ===

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
    await message.answer("🎉 **Оплата прошла успешно!** Подписка активирована. Теперь у тебя безлимитный доступ!")

@dp.message(F.text.startswith("http"))
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
                caption="✅ Вот твое видео без водяных знаков!\n\n🤖 Скачано через бота"
            )
            if not user["is_subscribed"]:
                await increment_downloads(user_id)
        else:
            await message.answer("⚠️ Не удалось выкачать видео. Проверь ссылку или попробуй другую.")
    finally:
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Заглушка порта запущена на порту {port}")

async def main():
    await init_db()
    await start_dummy_server()
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
