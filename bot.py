import asyncio
import json

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import TOKEN, ADMIN_ID

bot = Bot(TOKEN)
dp = Dispatcher()

user_data = {}

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇨🇳 Xitoy tovarlari buyurtma botiga xush kelibsiz!\n\n"
        "Mahsulot kodini yuboring (masalan: A102)."
    )

@dp.message()
async def product(message: Message):
    text = message.text

    # Rang tanlash
    if text in ["Qora", "Oq", "Ko'k"]:
        user_data[message.from_user.id]["color"] = text

        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="S"), KeyboardButton(text="M")],
                [KeyboardButton(text="L"), KeyboardButton(text="XL")],
                [KeyboardButton(text="XXL")]
            ],
            resize_keyboard=True
        )

        await message.answer("📏 O'lchamni tanlang:", reply_markup=kb)
        return

    # O'lcham tanlash
    if text in ["S", "M", "L", "XL", "XXL"]:
        user_data[message.from_user.id]["size"] = text
        await message.answer("🔢 Nechta olasiz? (Masalan: 2)")
        return

    # Soni
    if text.isdigit():
        order = user_data[message.from_user.id]
        order["count"] = text

        await bot.send_message(
            ADMIN_ID,
            f"🛒 YANGI BUYURTMA\n\n"
            f"📦 {order['name']}\n"
            f"🎨 Rang: {order['color']}\n"
            f"📏 O'lcham: {order['size']}\n"
            f"🔢 Soni: {order['count']}"
        )

        await message.answer(
            "✅ Buyurtmangiz qabul qilindi!\n\n"
            "📦 Tovar Xitoydan buyurtma qilinadi.\n"
            "🚚 Yetib kelgach sizga xabar beramiz."
        )
        return

    # Mahsulot kodi
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

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c)] for c in product["colors"]],
        resize_keyboard=True
    )

    await message.answer(
        f"📦 {product['name']}\n"
        f"💰 {product['price']} so'm\n\n"
        "🎨 Rangni tanlang:",
        reply_markup=kb
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
