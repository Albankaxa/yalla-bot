import os
import asyncio
import aiohttp
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates

# 🔐 Токен из переменной окружения
API_TOKEN = os.getenv("YOUR_BOT_TOKEN")

# 🛠 Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🛑 Проверка на наличие токена
if not API_TOKEN:
    logger.error("❌ Токен не найден. Завершаем работу.")
    exit(1)

# 📡 Проверка и удаление webhook
async def check_and_delete_webhook():
    base_url = f"https://api.telegram.org/bot{API_TOKEN}"
    async with aiohttp.ClientSession() as session:
        try:
            # getMe
            async with session.get(f"{base_url}/getMe") as response:
                if response.status == 200:
                    data = await response.json()
                    bot_info = data['result']
                    logging.info(f"✅ Бот найден: {bot_info['first_name']} (@{bot_info['username']})")
                else:
                    logging.error(f"❌ Ошибка при getMe: {response.status}")
                    return

            # getWebhookInfo
            async with session.get(f"{base_url}/getWebhookInfo") as response:
                if response.status == 200:
                    data = await response.json()
                    webhook_info = data['result']
                    logging.info(f"📡 Webhook URL: {webhook_info.get('url', 'Не установлен')}")
                    logging.info(f"📊 Pending updates: {webhook_info.get('pending_update_count', 0)}")
                    logging.info(f"🔄 Last error: {webhook_info.get('last_error_message', 'Нет')}")
                    if webhook_info.get("last_error_date"):
                        error_time = datetime.fromtimestamp(webhook_info["last_error_date"])
                        logging.info(f"🕒 Время последней ошибки: {error_time}")

                    # Удаляем webhook
                    if webhook_info.get('url'):
                        logging.info("🔄 Удаляем webhook...")
                        async with session.post(
                            f"{base_url}/deleteWebhook",
                            json={"drop_pending_updates": True}
                        ) as del_response:
                            if del_response.status == 200:
                                logging.info("✅ Webhook удален")
                            else:
                                logging.error(f"❌ Ошибка при удалении webhook: {del_response.status}")
        except Exception as e:
            logging.exception(f"❌ Ошибка при проверке webhook: {e}")

# Инициализация aiogram
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 🧭 Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row(
    KeyboardButton("📌 Работа"),
    KeyboardButton("🏠 Аренда жилья")
)
main_menu.row(
    KeyboardButton("🚗 Продажа авто"),
    KeyboardButton("🎉 Мероприятия")
)

# Команды
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для помощи русскоязычным жителям Израиля 🇮🇱",
        reply_markup=main_menu
    )

@dp.message_handler(lambda msg: msg.text == "📌 Работа")
async def jobs_handler(message: types.Message):
    await message.answer("🧑‍💼 Здесь будут вакансии. В будущем добавим выбор города.")

@dp.message_handler(lambda msg: msg.text == "🏠 Аренда жилья")
async def rent_handler(message: types.Message):
    await message.answer("🏡 Здесь будут предложения по аренде жилья.")

@dp.message_handler(lambda msg: msg.text == "🚗 Продажа авто")
async def cars_handler(message: types.Message):
    await message.answer("🚘 Здесь будут объявления о продаже автомобилей.")

@dp.message_handler(lambda msg: msg.text == "🎉 Мероприятия")
async def events_handler(message: types.Message):
    await message.answer("🎭 Здесь будут анонсы мероприятий по городам.")

# 🚀 Startup: сначала удалим Webhook
async def on_startup(dp: Dispatcher):
    await check_and_delete_webhook()
    logger.info("🚀 Запуск polling после очистки Webhook")

# 🔁 Основной запуск
if __name__ == "__main__":
    try:
        logger.info("📦 Запуск бота")
        executor.start_polling(dp, on_startup=on_startup)
    except TerminatedByOtherGetUpdates:
        logger.error("❌ Бот уже запущен в другом месте (polling).")
    except Exception as e:
        logger.exception(f"❌ Неизвестная ошибка: {e}")
