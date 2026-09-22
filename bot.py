import asyncio
import logging
import os
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

BOT_TOKEN = os.getenv("BOT_TOKEN")          # Render'da Environment Variable orqali beriladi
ADMIN_ID = int(os.getenv("ADMIN_ID", "1717518699"))
PORT = int(os.getenv("PORT", "10000"))

# ============================================================
#  MAHSULOTLAR BAZASI
#  Yangi mahsulot qo'shish uchun shunchaki pastga yana bitta
#  "KOD": {...} qatorini qo'shing.
# ============================================================

PRODUCTS = {
    "A103": {
        "name": "Nike futbolka",
        "price": 199000,
        "colors": ["Qora", "Oq"],
        "sizes": ["M", "X", "XL", "XXL"],
    },
}
PRODUCTS = {
    "A101": {
        "name": "Nike air krasofka",
        "price": 149000,
        "colors": ["Qora", "Oq"],
        "sizes": ["39", "40", "41", "42"],
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


# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================


def colors_keyboard(colors):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=c, callback_data=f"color:{c}")] for c in colors
        ]
    )
    return kb


def sizes_keyboard(sizes):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s, callback_data=f"size:{s}")] for s in sizes
        ]
    )
    return kb


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
    await message.answer(
        f"✅ <b>{product['name']}</b>\n"
        f"Narxi: {format_price(product['price'])}\n\n"
        f"Rangni tanlang:",
        parse_mode="HTML",
        reply_markup=colors_keyboard(product["colors"]),
    )
    await state.set_state(Order.waiting_color)


@dp.callback_query(Order.waiting_color, F.data.startswith("color:"))
async def handle_color(callback: CallbackQuery, state: FSMContext):
    color = callback.data.split(":", 1)[1]
    data = await state.get_data()
    product = PRODUCTS[data["code"]]

    await state.update_data(color=color)
    await callback.message.edit_text(
        f"Rang: <b>{color}</b>\n\nEndi o'lchamni tanlang:",
        parse_mode="HTML",
        reply_markup=sizes_keyboard(product["sizes"]),
    )
    await state.set_state(Order.waiting_size)
    await callback.answer()


@dp.callback_query(Order.waiting_size, F.data.startswith("size:"))
async def handle_size(callback: CallbackQuery, state: FSMContext):
    size = callback.data.split(":", 1)[1]
    await state.update_data(size=size)

    await callback.message.edit_text(
        f"O'lcham: <b>{size}</b> ✅\n\n"
        f"Endi telefon raqamingizni yozing (masalan: +998901234567):",
        parse_mode="HTML",
    )
    await state.set_state(Order.waiting_phone)
    await callback.answer()


@dp.message(Order.waiting_phone)
async def handle_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()
    product = PRODUCTS[data["code"]]

    summary = (
        f"🛒 <b>Buyurtma tasdiqlandi!</b>\n\n"
        f"Mahsulot: {product['name']}\n"
        f"Kod: {data['code']}\n"
        f"Rang: {data['color']}\n"
        f"O'lcham: {data['size']}\n"
        f"Narxi: {format_price(product['price'])}\n"
        f"Telefon: {phone}\n\n"
        f"Tez orada operator siz bilan bog'lanadi. Rahmat!"
    )

    await message.answer(summary, parse_mode="HTML")

    # Adminga (sizga) yuborish
    user = message.from_user
    admin_text = (
        f"🆕 <b>Yangi buyurtma</b>\n"
        f"Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Mijoz: {user.full_name} (@{user.username or 'yoq'})\n"
        f"User ID: {user.id}\n\n"
        f"Mahsulot: {product['name']}\n"
        f"Kod: {data['code']}\n"
        f"Rang: {data['color']}\n"
        f"O'lcham: {data['size']}\n"
        f"Narxi: {format_price(product['price'])}\n"
        f"Telefon: {phone}"
    )
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")

    await state.clear()
    await message.answer(
        "Yangi buyurtma berish uchun yana kod yuboring, "
        "yoki /start bosing."
    )
    await state.set_state(Order.waiting_code)


@dp.message()
async def fallback(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Boshlash uchun /start bosing.")


# ============================================================
#  RENDER UCHUN MINIMAL WEB SERVER (health check)
#  Render bepul Web Service PORT'ni tinglashni talab qiladi.
# ============================================================


async def health(request):
    return web.Response(text="Bot ishlayapti ✅")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
