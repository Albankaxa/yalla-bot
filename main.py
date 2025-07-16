
import logging
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = 'YOUR_BOT_TOKEN'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("👋 Привет! Добро пожаловать в Yalla Bot!\nВыберите категорию:\n1. Работа\n2. Аренда\n3. Авто\n...")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
