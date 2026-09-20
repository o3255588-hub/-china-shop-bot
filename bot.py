from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
import asyncio

TOKEN = 8904591770:AAH5kZ9MCg6PmEMgUwSMvEfm8_tc1Nsnk6U

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Assalomu alaykum!\n\n"
        "Xitoy tovarlari buyurtma botiga xush kelibsiz.\n"
        "Mahsulot kodini yuboring. Masalan: A102"
    )

@dp.message()
async def product_code(message: Message):
    code = message.text.upper()
    await message.answer(f"Siz yuborgan kod: {code}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
