import logging
import asyncio
from math import ceil
from aiogram import Bot, Dispatcher, types, F
from pydrive2.auth import GoogleAuth
from io import BytesIO
from pydrive2.drive import GoogleDrive
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
    Message
)
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
    save_receipt,
    update_balance,
    check_and_grant_referral_bonus,
    get_pending_payments,
    is_admin,
)


# Состояния
class PaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_photo = State()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

gauth = GoogleAuth()
gauth.LoadCredentialsFile("token.json")
if gauth.credentials is None:
    gauth.LocalWebserverAuth(access_type='offline')
elif gauth.access_token_expired:
    gauth.Refresh()
else:
    gauth.Authorize()
gauth.SaveCredentialsFile("token.json")
drive = GoogleDrive(gauth)

# ========= Константы =========
MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Купить ключ")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="👥 Рефералы")]
    ],
    resize_keyboard=True
)

# ========= /start =========
@dp.message(Command("start"))
async def start(msg: types.Message):
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(msg.from_user.id, ref)

    await msg.answer(
        "👋 Привет! Это магазин ключей.\n\n"
        "Выберите действие через меню снизу 👇",
        reply_markup=MAIN_MENU
    )

# ========= Обработка нажатий кнопок из меню =========
@dp.message(F.text == "💰 Баланс")
@dp.message(Command("balance"))
async def show_balance(msg: types.Message):
    check_and_grant_referral_bonus(msg.from_user.id)
    balance = get_balance(msg.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пополнить баланс", callback_data="add_balance")]
    ])
    await msg.answer(f"💰 Ваш текущий баланс: {balance} ₽", reply_markup=keyboard)

@dp.message(F.text == "🛒 Купить ключ")
@dp.message(Command("buy"))
async def list_products(msg: types.Message):
    products = get_all_products()
    if not products:
        await msg.answer("❌ Нет доступных товаров для покупки.", reply_markup=MAIN_MENU)
        return

    text = "🛍️ Доступные товары:"
    buttons = [
        [InlineKeyboardButton(text=p[1], callback_data=f"product_{p[0]}")] for p in products
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await msg.answer(text, reply_markup=keyboard)

@dp.message(F.text == "👥 Рефералы")
@dp.message(Command("ref"))
async def show_ref_link(msg: types.Message):
    user_id = msg.from_user.id
    link = f"https://t.me/{(await bot.me()).username}?start={user_id}"
    await msg.answer(
        f"👥 Ваша реферальная ссылка:\n\n{link}\n\n"
        "Приглашайте друзей — получите бонус 100 ₽, если они купят товаров на 2000 ₽.",
        reply_markup=MAIN_MENU
    )

# ========= Просмотр товара =========
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
        f"💰 Цена: {product[3]} ₽"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить", callback_data=f"buy_confirm_{product[0]}"),
         InlineKeyboardButton(text="Назад", callback_data="back_to_list")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ========= Покупка =========
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

    # Если хватает баланса
    if balance >= price:
        key = buy_key_by_product_id(product_id, user_id)
        if key:
            await callback.message.edit_text(
                f"✅ Покупка успешна!\nВаш ключ:\n<code>{key}</code>",
                parse_mode="HTML"
            )
            await bot.send_message(
                callback.from_user.id,
                "Главное меню 👇",
                reply_markup=MAIN_MENU
            )
        else:
            await callback.message.edit_text("❌ Ключей для этого товара больше нет.")
            await bot.send_message(
                callback.from_user.id,
                "Главное меню 👇",
                reply_markup=MAIN_MENU
            )
        await callback.answer()
        return

    # Иначе — создаём счёт
    payment_details = (
        "Реквизиты для оплаты:\n"
        "🏦 Банк: ТестБанк\n"
        "💳 Счёт: 1234 5678 9012 3456\n"
        "👤 Получатель: Тестовый Получатель\n\n"
        "Отправьте квитанцию после оплаты, проверка до 2 часов."
    )
    amount = product[3]
    order_name = product[1]
    payment_id = create_payment(user_id, amount, order_name, payment_details)

    text = (
        f"💳 Оплата товара <b>{order_name}</b>\n\n"
        f"Номер счёта: {payment_id}\n"
        f"Сумма: {amount} ₽\n"
        f"Статус: на рассмотрении\n\n"
        f"{payment_details}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment_{payment_id}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_list")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "add_balance")
async def add_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💳 Введите сумму пополнения (от 100 ₽):")
    await callback.answer()
    await state.set_state(PaymentStates.waiting_for_amount)

@dp.message(PaymentStates.waiting_for_amount, F.text.regexp(r"^\d{3,20}$"))
async def handle_balance_input(msg: Message, state: FSMContext):
    amount = int(msg.text)
    if amount < 100:
        await msg.answer("❌ Сумма должна быть от 100 ₽.")
        return

    payment_details = (
            "Реквизиты для оплаты:\n"
            "🏦 Банк: Сбербанк(МИР)\n"
            "💳 Счёт: 2202 2032 0643 2389\n"
            "👤 Получатель: Золин М.П.\n\n"
        )

    user_id = msg.from_user.id
    payment_id = create_payment(user_id, amount, "Пополнение баланса", payment_details)

    await msg.answer(
        f"💰 Пополнение баланса\n\n"
        f"Номер счёта: {payment_id}\n"
        f"Сумма: {amount} ₽\n"
        f"{payment_details}"
        "📸 Отправьте фото (скриншот оплаты)"
    )

    await state.update_data(payment_id=payment_id)
    await state.set_state(PaymentStates.waiting_for_photo)

@dp.message(PaymentStates.waiting_for_photo, ~F.photo)
async def wrong_input(msg: Message):
    await msg.answer("❗ Пожалуйста, отправьте именно *фото* (картинку), а не файл или текст.")

@dp.message(PaymentStates.waiting_for_photo, F.photo)
async def get_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data['payment_id']

    file = await msg.bot.get_file(msg.photo[-1].file_id)
    img_bytes = await msg.bot.download_file(file.file_path)

    image_data = BytesIO(img_bytes.read())

    try:
        gfile = drive.CreateFile({'title': f"payment_{payment_id}.jpg"})
        gfile.content = image_data  # передаём поток байтов напрямую
        gfile.Upload()
        gfile.InsertPermission({"role": "reader", "type": "anyone"})
        file_url = gfile['alternateLink']
    except:
        await msg.answer("Не удалось загрузить скриншот, отправьте скриншот в поддержку")
        return
    save_receipt(payment_id, file_url)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_user_payment_{payment_id}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="balance_back")]
    ])

    await msg.answer(
        "✅ Фото получено и загружено!\nТеперь нажмите подтверждение 👇",
        reply_markup=keyboard
    )

    await state.clear()
            
# ========= Подтверждение оплаты =========
@dp.callback_query(lambda c: c.data and c.data.startswith("confirm_user_payment_"))
async def confirm_payment(callback: CallbackQuery):
    payment_id = int(callback.data.split("_")[-1])
    payment = get_payment(payment_id)
    if not payment:
        await callback.answer("Платёж не найден.", show_alert=True)
        return

    set_payment_status(payment_id, "На рассмотрении")

    await callback.message.edit_text(
        "✅ Ваша заявка на рассмотрении.\n"
        "Ожидайте подтверждения администратора."
    )
    await bot.send_message(
        callback.from_user.id,
        "Главное меню 👇",
        reply_markup=MAIN_MENU
    )
    await callback.answer()

# ========= Подтверждение платежа администратором =========
@dp.message(Command("confirm"))
async def admin_confirm_payment(msg: types.Message):
    args = msg.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await msg.answer("⚠️ Использование: /confirm <payment_id>")
        return

    payment_id = int(args[1])

    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Только администратор может подтверждать платежи.")
        return

    # Получаем платёж
    payment = get_payment(payment_id)
    if not payment:
        await msg.answer("❌ Платёж не найден.")
        return

    set_payment_status(payment_id, "Оплачено")
    user_id = payment[1]
    amount = payment[2]
    update_balance(user_id, amount)

    await msg.answer(f"✅ Платёж №{payment_id} подтверждён.\nБаланс пользователя {user_id} пополнен на {amount} ₽.")


# ========= Навигация назад =========
@dp.callback_query(lambda c: c.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    products = get_all_products()
    text = "🛍️ Доступные товары:" if products else "❌ Нет товаров."
    buttons = [[InlineKeyboardButton(text=p[1], callback_data=f"product_{p[0]}")] for p in products]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if products else None
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "balance_back")
async def back_to_balance(callback: CallbackQuery):
    balance = get_balance(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пополнить баланс", callback_data="add_balance")]
    ])
    await callback.message.edit_text(f"💰 Ваш баланс: {balance} ₽", reply_markup=keyboard)
    await callback.answer()

@dp.message(Command("payments"))
async def list_pending_payments(msg: types.Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ У вас нет прав для просмотра этой информации.")
        return

    payments = get_pending_payments()
    if not payments:
        await msg.answer("✅ Нет платежей со статусом 'на рассмотрении'.")
        return

    await send_payments_page(msg.chat.id, payments, 1)


@dp.callback_query(lambda c: c.data and c.data.startswith("payments_page_"))
async def paginate_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для просмотра этой информации.", show_alert=True)
        return

    page = int(callback.data.split("_")[-1])
    payments = get_pending_payments()
    await send_payments_page(callback.message.chat.id, payments, page, callback.message)
    await callback.answer()


async def send_payments_page(chat_id: int, payments: list, page: int, message: types.Message | None = None):
    per_page = 10
    total_pages = ceil(len(payments) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    subset = payments[start:end]

    text_lines = []
    for p in subset:
        payment_id, user_id, amount, order_name, status, full_receipt = p
        text_lines.append(
            f"💳 <b>Платёж #{payment_id}</b>\n"
            f"👤 User ID: {user_id}\n"
            f"📦 {order_name}\n"
            f"💰 {amount} ₽\n"
            f"📄 Статус: {status}\n"
            f" ссылка на диск: {full_receipt}\n"
            f"-----------------------------"
        )

    text = "\n".join(text_lines)
    text += f"\n📄 Страница {page}/{total_pages}"

    # Кнопки пагинации
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"payments_page_{page - 1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"payments_page_{page + 1}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])

    if message:
        await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)


# ========= MAIN =========
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
