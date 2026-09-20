import asyncio
import json

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
)

# ==============================
# 🔑 SOZLAMALAR
# ==============================

# TOKENINGNI SHU YERGA YOZ
TOKEN = 8904591770:AAH5kZ9MCg6PmEMgUwSMvEfm8_tc1Nsnk6U

# O'Z TELEGRAM IDINGNI SHU YERGA YOZ
ADMIN_ID = 1717518699


# ==============================
# 🤖 BOT
# ==============================

bot = Bot(TOKEN)
dp = Dispatcher()

user_data = {}


# ==============================
# /start
# ==============================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇨🇳 Xitoy tovarlari buyurtma botiga xush kelibsiz!\n\n"
        "Mahsulot kodini yuboring.\n"
        "Masalan: A103"
    )


# ==============================
# MAHSULOT
# ==============================

@dp.message()
async def product(message: Message):

    text = message.text

    # products.json ni ochamiz
    with open("products.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    code = text.upper()

    # Mahsulot mavjudligini tekshirish
    if code not in products:
        await message.answer(
            "❌ Bunday mahsulot kodi topilmadi."
        )
        return

    product = products[code]

    # Foydalanuvchi ma'lumotlarini saqlash
    user_data[message.from_user.id] = {
        "code": code,
        "name": product["name"],
        "price": product["price"]
    }

    # Rang tugmalari
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=color)]
            for color in product["colors"]
        ],
        resize_keyboard=True
    )

    # Rasmni yuklash
    photo = FSInputFile(
        f"images/{product['image']}"
    )

    # Rasm + mahsulot ma'lumotlari
    await message.answer_photo(
        photo=photo,
        caption=(
            f"📦 {product['name']}\n"
            f"💰 {product['price']} so'm\n\n"
            "🎨 Rangni tanlang:"
        ),
        reply_markup=keyboard
    )


# ==============================
# BOTNI ISHGA TUSHIRISH
# ==============================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
