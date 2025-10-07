import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import TOKEN
from db import init_db, add_user, get_available_keys, buy_key

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: types.Message):
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(msg.from_user.id, ref)
    await msg.answer(
        "👋 Привет! Это магазин ключей.\n\n"
        "📦 /buy — купить ключ\n💰 /balance — баланс\n👥 /ref — твоя реферальная ссылка"
    )

@dp.message(Command("buy"))
async def show_keys(msg: types.Message):
    keys = get_available_keys()
    if not keys:
        await msg.answer("❌ Нет доступных ключей.")
        return

    text = "\n".join([f"{k[0]}. 🔑 {k[1][:4]}****" for k in keys])
    await msg.answer(f"📦 Доступные ключи:\n{text}\n\n💬 Напиши номер ключа для покупки.")

@dp.message(lambda m: m.text.isdigit())
async def handle_buy(msg: types.Message):
    key_id = int(msg.text)
    key = buy_key(key_id)
    if not key:
        await msg.answer("❌ Ключ не найден или уже куплен.")
    else:
        await msg.answer(f"✅ Покупка успешна!\nВот твой ключ:\n`{key}`", parse_mode='Markdown')

@dp.message(Command("ref"))
async def ref_link(msg: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={msg.from_user.id}"
    await msg.answer(f"👥 Твоя реферальная ссылка:\n{link}")

@dp.message(lambda m: m.content_type == 'photo')
async def handle_payment(msg: types.Message):
    await msg.answer("📸 Скриншот получен! Админ проверит и пополнит баланс.")

async def main():
    init_db()  # создаём таблицы, если их нет
    # dp.include_router(dp)  # регистрируем роутеры
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
