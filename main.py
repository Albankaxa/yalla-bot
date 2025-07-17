import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Command
from collections import defaultdict
import asyncio  # добавлено для работы с asyncio.run

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
user_posts = {}
user_lang = defaultdict(lambda: "ru")

categories = {
    "work": "👷 Работа",
    "rent": "🏠 Аренда жилья",
    "car": "🚗 Продажа авто",
    "event": "🎭 Мероприятия",
    "sell": "📦 Барахолка",
    "free": "🎁 Даром"
}

CITIES = [
    "Тель-Авив", "Хайфа", "Иерусалим",
    "Беэр-Шева", "Ашдод", "Нетивот",
    "Ришон-ле-Цион", "Эйлат", "Холон", "Бат-Ям"
]

LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇺🇸 English",
    "he": "🇮🇱 עברית"
}

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for key, value in categories.items():
        kb.insert(InlineKeyboardButton(value, callback_data=f"cat_{key}"))
    kb.add(InlineKeyboardButton("📋 Мои объявления", callback_data="my_posts"))
    kb.add(InlineKeyboardButton("🌐 Язык", callback_data="change_lang"))
    kb.add(InlineKeyboardButton("📢 Поделиться ботом", switch_inline_query=""))
    return kb

def city_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for city in CITIES:
        kb.insert(InlineKeyboardButton(city, callback_data=f"city_{city}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories"))
    return kb

def lang_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for code, name in LANGUAGES.items():
        kb.insert(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("👋 Добро пожаловать в Yalla Bot!\nВыберите категорию:", reply_markup=main_menu())

@dp.message_handler(commands=["help"])
async def help_command(message: types.Message):
    await message.answer("Чтобы опубликовать объявление, нажмите /start и следуйте инструкциям.")

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if message.from_user.id != MODERATOR_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    total_users = len(user_posts)
    total_posts = sum(len(posts) for posts in user_posts.values())
    await message.answer(f"📊 Пользователей: {total_users}\n📋 Всего объявлений: {total_posts}")

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    lang = callback_query.data[5:]
    user_lang[user_id] = lang
    await callback_query.message.answer(f"✅ Язык установлен: {LANGUAGES[lang]}", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "change_lang")
async def change_language(callback_query: types.CallbackQuery):
    await callback_query.message.answer("🌐 Выберите язык:", reply_markup=lang_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def choose_category(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cat = callback_query.data[4:]
    user_data[user_id] = {"category": categories[cat]}
    user_state[user_id] = "city"
    await callback_query.message.answer("🌆 Выберите город:", reply_markup=city_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("city_"))
async def choose_city(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = callback_query.data[5:]
    if user_id not in user_data:
        await callback_query.message.answer("⚠️ Сессия устарела. Нажмите /start")
        return
    user_data[user_id]["city"] = city
    user_state[user_id] = "text"
    await callback_query.message.answer("✏️ Введите текст объявления:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "text")
async def enter_text(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["text"] = message.text
    user_state[user_id] = "contact"
    await message.answer("📞 Введите контакт: номер или @username")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "contact")
async def enter_contact(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["contact"] = message.text
    user_state[user_id] = "photo"
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📷 Загрузить фото", callback_data="wait_photo"),
        InlineKeyboardButton("⏭ Без фото", callback_data="skip_photo")
    )
    await message.answer("Добавьте фото или пропустите:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "wait_photo")
async def wait_for_photo(callback_query: types.CallbackQuery):
    user_state[callback_query.from_user.id] = "photo"
    await callback_query.message.answer("📸 Пришлите фото:")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_photo(message: types.Message):
    user_id = message.from_user.id
    if user_state.get(user_id) != "photo":
        return
    user_data[user_id]["photo"] = message.photo[-1].file_id
    await send_to_moderator(user_id)
    await message.answer("✅ Объявление отправлено на модерацию")
    user_state[user_id] = None

@dp.callback_query_handler(lambda c: c.data == "skip_photo")
async def skip_photo(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_data[user_id]["photo"] = None
    await send_to_moderator(user_id)
    await callback_query.message.answer("✅ Объявление отправлено на модерацию")
    user_state[user_id] = None

async def send_to_moderator(user_id):
    data = user_data[user_id]
    caption = (
        f"🗂 {data['category']}\n🏙 {data['city']}\n📝 {data['text']}\n📱 {data['contact']}"
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{user_id}")
    )
    if data.get("photo"):
        await bot.send_photo(MODERATOR_ID, data["photo"], caption=caption, reply_markup=kb)
    else:
        await bot.send_message(MODERATOR_ID, caption, reply_markup=kb)
    user_posts.setdefault(user_id, []).append({**data, "status": "На модерации"})

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    data = user_posts[user_id][-1]
    caption = (
        f"🗂 {data['category']}\n🏙 {data['city']}\n📝 {data['text']}\n📱 {data['contact']}"
    )
    if data.get("photo"):
        await bot.send_photo(TARGET_CHANNEL, data["photo"], caption=caption)
    else:
        await bot.send_message(TARGET_CHANNEL, caption)
    data["status"] = "Опубликовано"
    await callback_query.answer("✅ Опубликовано")

@dp.callback_query_handler(lambda c: c.data.startswith("decline_"))
async def decline(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    user_posts[user_id][-1]["status"] = "Отклонено"
    await bot.send_message(user_id, "❌ Ваше объявление было отклонено")
    await callback_query.answer("Отклонено")

@dp.callback_query_handler(lambda c: c.data == "my_posts")
async def my_posts(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    posts = user_posts.get(user_id)
    if not posts:
        await callback_query.message.answer("📭 У вас пока нет объявлений")
        return
    text = "\n\n".join([
        f"🗂 {p['category']}\n🏙 {p['city']}\n📝 {p['text']}\n📱 {p['contact']}\n📌 Статус: {p['status']}"
        for p in posts
    ])
    await callback_query.message.answer(f"📋 Ваши объявления:\n\n{text}")

if __name__ == '__main__':
    # Удаляем webhook перед запуском polling, чтобы избежать ошибки конфликта getUpdates
    asyncio.run(bot.delete_webhook())
    executor.start_polling(dp, skip_updates=True)
