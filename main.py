import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Command
from collections import defaultdict
import asyncio

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
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    # Очищаем состояние пользователя при старте
    user_state.pop(user_id, None)
    user_data.pop(user_id, None)
    await message.answer("👋 Добро пожаловать в Yalla Bot!\nВыберите категорию:", reply_markup=main_menu())

@dp.message_handler(commands=["help"])
async def help_command(message: types.Message):
    help_text = (
        "ℹ️ Как пользоваться ботом:\n\n"
        "1. Нажмите /start для начала работы\n"
        "2. Выберите категорию объявления\n"
        "3. Укажите город\n"
        "4. Введите текст объявления\n"
        "5. Добавьте контакт\n"
        "6. При желании добавьте фото\n"
        "7. Дождитесь модерации\n\n"
        "📋 Посмотреть свои объявления: /start → 'Мои объявления'\n"
        "🌐 Сменить язык: /start → 'Язык'"
    )
    await message.answer(help_text)

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
    await callback_query.message.edit_text(f"✅ Язык установлен: {LANGUAGES[lang]}", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "change_lang")
async def change_language(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("🌐 Выберите язык:", reply_markup=lang_menu())

@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("👋 Добро пожаловать в Yalla Bot!\nВыберите категорию:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    # Сбрасываем состояние пользователя
    user_state.pop(user_id, None)
    user_data.pop(user_id, None)
    await callback_query.message.edit_text("👋 Добро пожаловать в Yalla Bot!\nВыберите категорию:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def choose_category(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cat = callback_query.data[4:]
    user_data[user_id] = {"category": categories[cat]}
    user_state[user_id] = "city"
    await callback_query.message.edit_text("🌆 Выберите город:", reply_markup=city_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("city_"))
async def choose_city(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = callback_query.data[5:]
    if user_id not in user_data:
        await callback_query.message.edit_text("⚠️ Сессия устарела. Нажмите /start", reply_markup=None)
        return
    user_data[user_id]["city"] = city
    user_state[user_id] = "text"
    await callback_query.message.edit_text("✏️ Введите текст объявления:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "text")
async def enter_text(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем длину текста
    if len(message.text) > 1000:
        await message.answer("⚠️ Текст слишком длинный. Максимум 1000 символов.")
        return
    
    user_data[user_id]["text"] = message.text
    user_state[user_id] = "contact"
    await message.answer("📞 Введите контакт: номер телефона или @username")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "contact")
async def enter_contact(message: types.Message):
    user_id = message.from_user.id
    contact = message.text.strip()
    
    # Базовая валидация контакта
    if len(contact) < 3:
        await message.answer("⚠️ Контакт слишком короткий. Введите корректный номер или @username")
        return
    
    user_data[user_id]["contact"] = contact
    user_state[user_id] = "photo"
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📷 Загрузить фото", callback_data="wait_photo"),
        InlineKeyboardButton("⏭ Без фото", callback_data="skip_photo")
    )
    await message.answer("Добавьте фото или пропустите:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "wait_photo")
async def wait_for_photo(callback_query: types.CallbackQuery):
    user_state[callback_query.from_user.id] = "photo"
    await callback_query.message.edit_text("📸 Пришлите фото:")

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
    await callback_query.message.edit_text("✅ Объявление отправлено на модерацию")
    user_state[user_id] = None

async def send_to_moderator(user_id):
    try:
        data = user_data[user_id]
        caption = (
            f"🗂 {data['category']}\n🏙 {data['city']}\n📝 {data['text']}\n📱 {data['contact']}\n"
            f"👤 От пользователя: {user_id}"
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
    except Exception as e:
        logging.error(f"Ошибка при отправке модератору: {e}")
        await bot.send_message(user_id, "❌ Произошла ошибка при отправке. Попробуйте еще раз.")

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(callback_query: types.CallbackQuery):
    try:
        user_id = int(callback_query.data.split("_")[1])
        if user_id not in user_posts or not user_posts[user_id]:
            await callback_query.answer("❌ Объявление не найдено")
            return
            
        data = user_posts[user_id][-1]
        caption = (
            f"🗂 {data['category']}\n🏙 {data['city']}\n📝 {data['text']}\n📱 {data['contact']}"
        )
        if data.get("photo"):
            await bot.send_photo(TARGET_CHANNEL, data["photo"], caption=caption)
        else:
            await bot.send_message(TARGET_CHANNEL, caption)
        data["status"] = "Опубликовано"
        await bot.send_message(user_id, "✅ Ваше объявление опубликовано!")
        await callback_query.answer("✅ Опубликовано")
    except Exception as e:
        logging.error(f"Ошибка при одобрении: {e}")
        await callback_query.answer("❌ Ошибка при публикации")

@dp.callback_query_handler(lambda c: c.data.startswith("decline_"))
async def decline(callback_query: types.CallbackQuery):
    try:
        user_id = int(callback_query.data.split("_")[1])
        if user_id not in user_posts or not user_posts[user_id]:
            await callback_query.answer("❌ Объявление не найдено")
            return
            
        user_posts[user_id][-1]["status"] = "Отклонено"
        await bot.send_message(user_id, "❌ Ваше объявление было отклонено")
        await callback_query.answer("❌ Отклонено")
    except Exception as e:
        logging.error(f"Ошибка при отклонении: {e}")
        await callback_query.answer("❌ Ошибка при отклонении")

@dp.callback_query_handler(lambda c: c.data == "my_posts")
async def my_posts(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    posts = user_posts.get(user_id)
    if not posts:
        await callback_query.message.edit_text("📭 У вас пока нет объявлений", reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        ))
        return
    
    text = "📋 Ваши объявления:\n\n"
    for i, p in enumerate(posts, 1):
        text += f"{i}. 🗂 {p['category']}\n🏙 {p['city']}\n📝 {p['text'][:50]}{'...' if len(p['text']) > 50 else ''}\n📱 {p['contact']}\n📌 Статус: {p['status']}\n\n"
    
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    )
    await callback_query.message.edit_text(text, reply_markup=kb)

# Обработчик для всех остальных сообщений
@dp.message_handler()
async def handle_other_messages(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_state:
        await message.answer("⚠️ Пожалуйста, завершите текущее действие или нажмите /start для начала заново")
    else:
        await message.answer("👋 Привет! Нажмите /start для начала работы с ботом")

async def on_startup(dp):
    """Функция, которая выполняется при запуске бота"""
    try:
        await bot.delete_webhook()
        logging.info("Webhook удален")
    except Exception as e:
        logging.error(f"Ошибка при удалении webhook: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
