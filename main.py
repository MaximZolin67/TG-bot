import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import TOKEN
from db import (
    init_db,
    add_user,
    get_all_products,
    get_product_by_id,
    buy_key_by_product_id,
    create_payment,
    get_payment,
    set_payment_status,
    get_balance,
    update_balance,
    check_and_grant_referral_bonus,
    fill_test_data,
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== Команда /start ==========
@dp.message(Command("start"))
async def start(msg: types.Message):
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(msg.from_user.id, ref)
    await msg.answer(
        "👋 Привет! Это магазин ключей.\n\n"
        "📦 /buy — купить ключ\n💰 /balance — баланс\n👥 /ref — твоя реферальная ссылка"
    )

# ========== Добавление тестовых данных ==========
@dp.message(Command("init_testdata"))
async def init_test(msg: types.Message):
    fill_test_data()
    await msg.answer("Тестовые продукты и ключи успешно добавлены.")

# ========== Проверка баланса ==========
@dp.message(Command("balance"))
async def show_balance(msg: types.Message):
    check_and_grant_referral_bonus(msg.from_user.id)
    balance = get_balance(msg.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пополнить баланс", callback_data="add_balance")]
    ])

    await msg.answer(f"💰 Ваш текущий баланс: {balance} рублей.", reply_markup=keyboard)

# ========== Список товаров ==========
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

# ========== Детали товара ==========
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить", callback_data=f"buy_confirm_{product[0]}"),
         InlineKeyboardButton(text="Назад", callback_data="back_to_list")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ========== Подтверждение покупки ==========
@dp.callback_query(lambda c: c.data and c.data.startswith("buy_confirm_"))
async def show_payment_options(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    product = get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    user_id = callback.from_user.id
    balance = get_balance(user_id)
    price = product[3]

    # Если хватает баланса — сразу списываем и выдаём ключ
    if balance >= price:
        key = buy_key_by_product_id(product_id, user_id)
        if key:
            await callback.message.edit_text(f"✅ Покупка успешна!\nВаш ключ:\n<code>{key}</code>", parse_mode="HTML")
        else:
            await callback.message.edit_text("❌ Ключей для этого товара больше нет.")
        await callback.answer()
        return

    # Иначе — показываем реквизиты для ручной оплаты
    payment_details = (
        "Реквизиты для оплаты:\n"
        "Банк: ТестБанк\n"
        "Реквизиты: 1234 5678 9012 3456\n"
        "Получатель: Тестовый Получатель\n"
        "Назначение: Оплата товара\n\n"
        "Проверка платежа происходит вручную до 2 часов.\n"
        "Отправьте квитанцию фото после оплаты."
    )

    amount = product[3]
    order_name = product[1]
    payment_id = create_payment(user_id, amount, order_name, payment_details)

    text = (
        f"Оплата товара\n\n"
        f"Номер счёта: {payment_id}\n"
        f"Сумма к оплате: {amount} рублей\n"
        f"Статус: на рассмотрении\n\n"
        f"{payment_details}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить оплату", callback_data=f"confirm_payment_{payment_id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"product_{product_id}")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ========== Пополнение баланса ==========
@dp.callback_query(lambda c: c.data == "add_balance")
async def add_balance(callback: CallbackQuery):
    text = (
        "💳 Введите сумму пополнения (от 100 до 99999 ₽):\n"
        "После этого я создам платёж и покажу реквизиты."
    )
    await callback.message.edit_text(text)
    await callback.answer()

    # Ждём следующего сообщения от пользователя
    @dp.message(F.text.regexp(r"^\d{3,5}$"))
    async def handle_balance_input(msg: types.Message):
        amount = int(msg.text)
        if not (100 <= amount <= 99999):
            await msg.answer("❌ Сумма должна быть от 100 до 99999 ₽.")
            return

        payment_details = (
            "Реквизиты для оплаты:\n"
            "Банк: ТестБанк\n"
            "Реквизиты: 1234 5678 9012 3456\n"
            "Получатель: Тестовый Получатель\n"
            "Назначение: Пополнение баланса\n\n"
            "После оплаты отправьте квитанцию фото. Проверка — до 2 часов."
        )

        user_id = msg.from_user.id
        payment_id = create_payment(user_id, amount, "Пополнение баланса", payment_details)

        text = (
            f"💰 Пополнение баланса\n\n"
            f"Номер счёта: {payment_id}\n"
            f"Сумма к оплате: {amount} ₽\n"
            f"Статус: на рассмотрении\n\n"
            f"{payment_details}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment_{payment_id}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="balance_back")]
        ])

        await msg.answer(text, reply_markup=keyboard)
        # После успешного ввода обработчик можно удалить, чтобы не ловил другие числа
        dp.message.handlers.unregister(handle_balance_input)

# ========== Подтверждение платежа ==========
@dp.callback_query(lambda c: c.data and c.data.startswith("confirm_payment_"))
async def confirm_payment(callback: CallbackQuery):
    payment_id = int(callback.data.split("_")[2])
    payment = get_payment(payment_id)
    if not payment:
        await callback.answer("Платёж не найден.", show_alert=True)
        return

    set_payment_status(payment_id, "Оплачено")
    user_id = payment[1]
    amount = payment[2]
    update_balance(user_id, amount)

    await callback.message.edit_text(
        f"✅ Платёж №{payment_id} подтверждён.\nБаланс пополнен на {amount} ₽."
    )
    await callback.answer()

# ========== Назад к списку товаров ==========
@dp.callback_query(lambda c: c.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    products = get_all_products()
    text = "Вот список доступных товаров:" if products else "❌ Нет доступных товаров."
    buttons = [[InlineKeyboardButton(text=p[1], callback_data=f"product_{p[0]}")] for p in products]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if products else None

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ========== Назад к балансу ==========
@dp.callback_query(lambda c: c.data == "balance_back")
async def back_to_balance(callback: CallbackQuery):
    balance = get_balance(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пополнить баланс", callback_data="add_balance")]
    ])
    await callback.message.edit_text(f"💰 Ваш баланс: {balance} ₽", reply_markup=keyboard)
    await callback.answer()

# ========== MAIN ==========
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
