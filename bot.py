import asyncio
import csv
import io
import logging
import os
import time
from datetime import datetime

import aiohttp
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

# Google Jadvalning "Publish to web -> CSV" havolasi.
# Bu Render'da Environment Variable sifatida SHEET_CSV_URL nomi bilan beriladi.
SHEET_CSV_URL = os.getenv("SHEET_CSV_URL", "")

CACHE_TTL_SECONDS = 30  # necha soniyada bir marta jadvalni qayta o'qish
_cache = {"data": {}, "ts": 0}

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


# ============================================================
#  GOOGLE JADVALDAN MAHSULOTLARNI O'QISH
#  Jadval ustunlari (aynan shu tartibda va nomda bo'lishi kerak):
#  Kod | Nomi | Narxi | Ranglar | Olchamlar | Rasm
#  Ranglar va Olchamlar ustunida bir nechta qiymat vergul bilan
#  ajratiladi, masalan: Qora, Oq
# ============================================================


async def load_products():
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < CACHE_TTL_SECONDS):
        return _cache["data"]

    if not SHEET_CSV_URL:
        logging.warning("SHEET_CSV_URL sozlanmagan, mahsulotlar bo'sh bo'ladi.")
        return _cache["data"]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SHEET_CSV_URL, timeout=10) as resp:
                text = await resp.text()
    except Exception as e:
        logging.error(f"Jadvalni o'qishda xatolik: {e}")
        return _cache["data"]  # eski ma'lumot bilan davom etamiz

    products = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get("Kod") or "").strip().upper()
        if not code:
            continue

        colors = [c.strip() for c in (row.get("Ranglar") or "").split(",") if c.strip()]
        sizes = [s.strip() for s in (row.get("Olchamlar") or "").split(",") if s.strip()]

        raw_price = (row.get("Narxi") or "0").replace(" ", "").replace(",", "")
        try:
            price = int(raw_price)
        except ValueError:
            price = 0

        products[code] = {
            "name": (row.get("Nomi") or "").strip(),
            "price": price,
            "colors": colors or ["Standart"],
            "sizes": sizes or ["Standart"],
            "image": (row.get("Rasm") or "").strip(),
        }

    if products:
        _cache["data"] = products
        _cache["ts"] = now

    return _cache["data"]


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
    products = await load_products()
    product = products.get(code)

    if not product:
        await message.answer(
            "❌ Bunday kodli mahsulot topilmadi.\n"
            "Kodni tekshirib, qaytadan yuboring (masalan: A103)."
        )
        return

    await state.update_data(code=code)

    caption = (
        f"✅ <b>{product['name']}</b>\n"
        f"Narxi: {format_price(product['price'])}\n\n"
        f"Rangni tanlang:"
    )

    if product.get("image"):
        try:
            await message.answer_photo(
                photo=product["image"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=colors_keyboard(product["colors"]),
            )
        except Exception as e:
            logging.error(f"Rasm yuborishda xatolik: {e}")
            await message.answer(
                caption, parse_mode="HTML", reply_markup=colors_keyboard(product["colors"])
            )
    else:
        await message.answer(
            caption, parse_mode="HTML", reply_markup=colors_keyboard(product["colors"])
        )

    await state.set_state(Order.waiting_color)


@dp.callback_query(Order.waiting_color, F.data == "back:code")
async def back_to_code(callback: CallbackQuery, state: FSMContext):
    text = "Kanaldagi mahsulot rasmi ostidagi kodni shu yerga yuboring (masalan: <b>A103</b>):"

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, parse_mode="HTML")

    await state.set_state(Order.waiting_code)
    await callback.answer()


@dp.callback_query(Order.waiting_color, F.data.startswith("color:"))
async def handle_color(callback: CallbackQuery, state: FSMContext):
    color = callback.data.split(":", 1)[1]
    data = await state.get_data()
    products = await load_products()
    product = products.get(data["code"])

    if not product:
        await callback.answer("Mahsulot topilmadi, qaytadan urinib ko'ring.", show_alert=True)
        return

    await state.update_data(color=color)

    text = f"Rang: <b>{color}</b>\n\nEndi o'lchamni tanlang:"

