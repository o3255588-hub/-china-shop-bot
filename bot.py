import asyncio
import logging
import os
import random
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

logging.basicConfig(level=logging.INFO)

# ============================================================
#  SOZLAMALAR
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1717518699"))
PORT = int(os.getenv("PORT", "10000"))

# ============================================================
#  MAHSULOTLAR BAZASI
#  Yangi mahsulot qo'shish uchun pastga yana bitta
#  "KOD": {...} qatorini qo'shing, vergul bilan ajratib.
# ============================================================

PRODUCTS = {
    "A103": {
        "name": "Nike futbolka",
        "price": 199000,
        "colors": ["Qora", "Oq"],
        "sizes": ["M", "X", "XL", "XXL"],
    },
}

# ============================================================
#  HOLATLAR (FSM)
# ============================================================


class Order(StatesGroup):
    waiting_code = State()
    waiting_color = State()
    waiting_size = State()
    waiting_phone = State()


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Ishlatilgan buyurtma raqamlari (takrorlanmasligi uchun)
used_order_numbers = set()


def generate_order_number() -> int:
    while True:
        number = random.randint(1000000, 9999999)
        if number not in used_order_numbers:
            used_order_numbers.add(number)
            return number


# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================


def colors_keyboard(colors):
    buttons = [
        [InlineKeyboardButton(text=c, callback_data=f"color:{c}")] for c in colors
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back:code")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sizes_keyboard(sizes):
    buttons = [
        [InlineKeyboardButton(text=s, callback_data=f"size:{s}")] for s in sizes
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back:color")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ") + " so'm"


# ============================================================
#  HANDLERLAR
# ============================================================


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Kanaldagi mahsulot rasmi ostidagi kodni shu yerga yuboring "
        "(masalan: <b>A103</b>), men sizga buyurtma berishda yordam beraman.",
        parse_mode="HTML",
    )
    await state.set_state(Order.waiting_code)


@dp.message(Order.waiting_code)
async def handle_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    product = PRODUCTS.get(code)

    if not product:
        await message.answer(
            "❌ Bunday kodli mahsulot topilmadi.\n"
            "Kodni tekshirib, qaytadan yuboring (masalan: A103)."
        )
        return

    await state.update_data(code=code)

    text = (
        f"✅ <b>{product['name']}</b>\n"
        f"Narxi: {format_price(product['price'])}\n\n"
        f"Rangni tanlang:"
    )
    await message.answer(
        text, parse_mode="HTML", reply_markup=colors_keyboard(product["colors"])
    )
    await state.set_state(Order.waiting_color)


@dp.callback_query(Order.waiting_color, F.data == "back:code")
async def back_to_code(callback: CallbackQuery, state: FSMContext):
    text = "Kanaldagi mahsulot rasmi ostidagi kodni shu yerga yuboring (masalan: <b>A103</b>):"
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(Order.waiting_code)
    await callback.answer()


@dp.callback_query(Order.waiting_color, F.data.startswith("color:"))
async def handle_color(callback: CallbackQuery, state: FSMContext):
    color = callback.data.split(":", 1)[1]
    data = await state.get_data()
    product = PRODUCTS.get(data["code"])

    if not product:
        await callback.answer("Xatolik, /start bosing.", show_alert=True)
        return

    await state.update_data(color=color)

    text = f"Rang: <b>{color}</b>\n\nEndi o'lchamni tanlang:"
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=sizes_keyboard(product["sizes"])
    )
    await state.set_state(Order.waiting_size)
    await callback.answer()


@dp.callback_query(Order.waiting_size, F.data == "back:color")
async def back_to_color(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product = PRODUCTS.get(data["code"])

    if not product:
        await callback.answer("Xatolik, /start bosing.", show_alert=True)
        return

    text = (
        f"✅ <b>{product['name']}</b>\n"
        f"Narxi: {format_price(product['price'])}\n\n"
        f"Rangni tanlang:"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=colors_keyboard(product["colors"])
    )
    await state.set_state(Order.waiting_color)
    await callback.answer()


@dp.callback_query(Order.waiting_size, F.data.startswith("size:"))
async def handle_size(callback: CallbackQuery, state: FSMContext):
    size = callback.data.split(":", 1)[1]
    await state.update_data(size=size)

    text = f"O'lcham: <b>{size}</b> ✅\n\nEndi telefon raqamingizni yozing (masalan: +998901234567):"
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(Order.waiting_phone)
    await callback.answer()


@dp.message(Order.waiting_phone)
async def handle_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()
    product = PRODUCTS.get(data["code"])

    if not product:
        await message.answer("Xatolik yuz berdi, /start bosib qaytadan urinib ko'ring.")
        await state.clear()
        return

    order_number = generate_order_number()

    summary = (
        f"🛒 <b>Buyurtma tasdiqlandi!</b>\n\n"
        f"Buyurtma raqami: <b>#{order_number}</b>\n\n"
        f"Mahsulot: {product['name']}\n"
        f"Kod: {data['code']}\n"
        f"Rang: {data['color']}\n"
        f"O'lcham: {data['size']}\n"
        f"Narxi: {format_price(product['price'])}\n"
        f"Telefon: {phone}\n\n"
        f"Savol bo'lsa, shu raqamni ayting: <b>#{order_number}</b>\n"
        f"Tez orada operator siz bilan bog'lanadi. Rahmat!"
    )
    await message.answer(summary, parse_mode="HTML")

    user = message
