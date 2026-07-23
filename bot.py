from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.client.session.aiohttp import AiohttpSession  # <-- Добавили сессию

from config import BOT_TOKEN, FREE_DAILY_LIMIT, SUB_PRICE
from database import init_db, get_or_create_user, increment_downloads, activate_subscription
from downloader import download_media

# Настраиваем сессию с увеличенным таймаутом (5 минут = 300 секунд)
session = AiohttpSession(timeout=300)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Кнопка для оплаты
def get_pay_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Купить Безлимит — {SUB_PRICE} ₽ / мес", callback_data="buy_sub")]
    ])
    return kb

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await get_or_create_user(message.from_user.id)
    await message.answer(
        "👋 **Салют! Я качаю видео без водяных знаков** из TikTok, Reels, Shorts и Pinterest!\n\n"
        "🔗 Просто отправь мне ссылку на видео.\n"
        f"📊 Твой лимит: {FREE_DAILY_LIMIT} бесплатное скачивание в день.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_sub")
async def process_buy_sub(callback: types.CallbackQuery):
    # Telegram Stars (1 звезда ≈ 1.5 - 2 рубля)
    stars_amount = int(SUB_PRICE / 2)
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Безлимитная подписка",
        description="Скачивание любых видео без ограничений и лимитов на 30 дней.",
        payload="sub_monthly_payload",
        provider_token="", # Пусто для Telegram Stars!
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

    # Проверка лимитов
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
            os.remove(file_path) # Очищаем временный файл

async def handle_healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render сам передает номер порта в переменную окружения PORT
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Заглушка порта запущена на порту {port}")

async def main():
    await init_db()
    await start_dummy_server()  # <--- Запускаем слушатель порта для Render
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
