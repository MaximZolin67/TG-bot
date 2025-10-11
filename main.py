import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import TOKEN
from db import init_db, add_user, get_all_products, get_product_by_id, buy_key_by_product_id

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
async def list_products(msg: types.Message):
    products = get_all_products()
    if not products:
        await msg.answer("❌ Нет доступных товаров для покупки.")
        return

    text = "Вот список доступных для покупки товаров:"
    buttons = [
        [InlineKeyboardButton(text=p[1], callback_data=f"product_{p[0]}")] for p in products
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await msg.answer(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith("product_"))
async def show_product_detail(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    text = (
        f"🛒 <b>{product[1]}</b>\n\n"
        f"{product[2] or 'Описание отсутствует.'}\n\n"
        f"💰 Цена: {product[3]} руб."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Купить", callback_data=f"buy_{product_id}"),
                InlineKeyboardButton(text="Назад", callback_data="back_to_list"),
            ]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def buy_product_key(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    key = buy_key_by_product_id(product_id, callback.from_user.id)
    if not key:
        await callback.answer("Ключи для этого товара закончились или товар не найден.", show_alert=True)
        return

    text = f"✅ Покупка успешна!\nВот твой ключ:\n`{key}`"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "back_to_list")
async def back_to_product_list(callback: CallbackQuery):
    products = get_all_products()
    if not products:
        await callback.message.edit_text("❌ Нет доступных товаров для покупки.", reply_markup=None)
        await callback.answer()
        return

    text = "Вот список доступных для покупки товаров:"
    buttons = [
        [InlineKeyboardButton(text=p[1], callback_data=f"product_{p[0]}")] for p in products
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
