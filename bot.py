import asyncio
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config import TOKEN, ADMIN_ID
TOKEN = 8904591770:AAH5kZ9MCg6PmEMgUwSMvEfm8_tc1Nsnk6U
ADMIN_ID = 1717518699

bot = Bot(TOKEN)
dp = Dispatcher()

user_data = {}


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇨🇳 Xitoy tovarlari buyurtma botiga xush kelibsiz!\n\n"
        "Mahsulot kodini yuboring.\nMasalan: A102"
    )


@dp.message()
async def product(message: Message):
    text = message.text

    if text in ["Qora", "Oq", "Ko'k"]:
        user_data[message.from_user.id]["color"] = text
        await message.answer(f"✅ Rang tanlandi: {text}")
        return

    code = text.upper()

    with open("products.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    if code not in products:
        await message.answer("❌ Bunday mahsulot kodi topilmadi.")
        return

    product = products[code]

    user_data[message.from_user.id] = {
        "code": code,
        "name": product["name"]
    }

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c)] for c in product["colors"]],
        resize_keyboard=True
    )

    await message.answer(
        f"📦 {product['name']}\n"
        f"💰 {product['price']} so'm\n\n"
        "🎨 Rangni tanlang:",
        reply_markup=keyboard
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
