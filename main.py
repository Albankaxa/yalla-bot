
import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = os.getenv("YOUR_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("❌ Ошибка: переменная окружения 'YOUR_BOT_TOKEN' не задана.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

MODERATOR_ID = 884963545
TARGET_CHANNEL = "@yallaisrael"

user_state = {}
user_data = {}

categories = {
    "work": "👷 Работа",
    "rent": "🏠 Аренда жилья",
    "car": "🚗 Продажа авто",
    "event": "🎭 Мероприятия",
    "sell": "📦 Барахолка",
    "free": "🎁 Даром"
}

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for key, value in categories.items():
        kb.insert(InlineKeyboardButton(value, callback_data=f"cat_{key}"))
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
    """👋 Добро пожаловать в Yalla Bot!
Выберите категорию:""",
    reply_markup=main_menu()
)

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def process_category(callback_query: types.CallbackQuery):
    category_key = callback_query.data[4:]
    user_id = callback_query.from_user.id
    user_state[user_id] = "city"
    user_data[user_id] = {"category": categories[category_key]}
    await bot.send_message(user_id, "🏙 Введите город:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "city")
async def process_city(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["city"] = message.text
    user_state[user_id] = "text"
    await message.answer("📝 Введите текст объявления:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "text")
async def process_text(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["text"] = message.text
    user_state[user_id] = "contact"
    await message.answer("📱 Введите контакт (номер или Telegram @username):")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "contact")
async def process_contact(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["contact"] = message.text
    user_state[user_id] = "photo"
    await message.answer("📷 Прикрепите фото (или отправьте 'Нет'):")

@dp.message_handler(content_types=["photo", "text"])
async def process_photo(message: types.Message):
    user_id = message.from_user.id
    if user_state.get(user_id) != "photo":
        return
    user_data[user_id]["photo"] = message.photo[-1].file_id if message.photo else None
    user_state[user_id] = "done"

    data = user_data[user_id]
    caption = f"🗂 Категория: {data['category']}
🏙 Город: {data['city']}
📝 {data['text']}
📱 {data['contact']}"

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{user_id}")
    )

    if data["photo"]:
        await bot.send_photo(MODERATOR_ID, data["photo"], caption=caption, reply_markup=kb)
    else:
        await bot.send_message(MODERATOR_ID, caption, reply_markup=kb)

    await message.answer("✅ Ваше объявление отправлено на модерацию.")
    user_state[user_id] = None

@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("decline_"))
async def handle_moderation(callback_query: types.CallbackQuery):
    action, user_id = callback_query.data.split("_")
    user_id = int(user_id)
    data = user_data.get(user_id)
    if not data:
        await callback_query.answer("❌ Данные не найдены")
        return

    caption = f"🗂 Категория: {data['category']}
🏙 Город: {data['city']}
📝 {data['text']}
📱 {data['contact']}"
    if action == "approve":
        if data["photo"]:
            await bot.send_photo(TARGET_CHANNEL, data["photo"], caption=caption)
        else:
            await bot.send_message(TARGET_CHANNEL, caption)
        await callback_query.answer("✅ Объявление опубликовано")
    else:
        await callback_query.answer("❌ Объявление отклонено")
        await bot.send_message(user_id, "❌ Ваше объявление было отклонено модератором.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
