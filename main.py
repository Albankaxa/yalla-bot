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
user_posts = {}  # хранение объявлений пользователя с их статусом

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
    "Ришон-ле-Цион", "Эйлат", "Холон",
    "Бат-Ям"
]

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for key, value in categories.items():
        kb.insert(InlineKeyboardButton(value, callback_data=f"cat_{key}"))
    kb.add(InlineKeyboardButton("📋 Мои объявления", callback_data="my_posts"))
    return kb

def city_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for city in CITIES:
        kb.insert(InlineKeyboardButton(city, callback_data=f"city_{city}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories"))
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в Yalla Bot!\nВыберите категорию:",
        reply_markup=main_menu()
    )

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def process_category(callback_query: types.CallbackQuery):
    category_key = callback_query.data[4:]
    user_id = callback_query.from_user.id
    user_state[user_id] = "city"
    user_data[user_id] = {"category": categories[category_key]}
    await bot.send_message(user_id, "🌆 Выберите город:", reply_markup=city_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("city_"))
async def process_city_choice(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = callback_query.data[5:]
    if user_id not in user_data:
        await callback_query.message.answer("⚠️ Сессия потеряна. Начните заново: /start")
        return
    user_data[user_id]["city"] = city
    user_state[user_id] = "text"
    await bot.send_message(user_id, "📝 Введите текст объявления:")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "text")
async def process_text(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("⚠️ Сессия потеряна. Начните заново: /start")
        return
    user_data[user_id]["text"] = message.text
    user_state[user_id] = "confirm"

    data = user_data[user_id]
    preview = (
        f"📂 Предпросмотр объявления:\n"
        f"📄 Категория: {data['category']}\n"
        f"🌆 Город: {data['city']}\n"
        f"📝 {data['text']}"
    )

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_text"),
        InlineKeyboardButton("✏️ Редактировать текст", callback_data="edit_text"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel_post")
    )
    await message.answer(preview, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "edit_text")
async def edit_text(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_state[user_id] = "text"
    await callback_query.message.answer("📝 Пожалуйста, введите новый текст объявления:")

@dp.callback_query_handler(lambda c: c.data == "confirm_text")
async def confirm_text(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_state[user_id] = "contact"
    await callback_query.message.answer("📞 Введите контакт (номер или @username):")

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "contact")
async def process_contact(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["contact"] = message.text
    user_state[user_id] = "photo"

    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📷 Загрузить фото", callback_data="wait_photo"),
        InlineKeyboardButton("⏭ Пропустить", callback_data="skip_photo")
    )
    await message.answer("📷 Прикрепите фото или нажмите 'Пропустить':", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "skip_photo")
async def skip_photo(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_data[user_id]["photo"] = None
    await submit_to_moderation(user_id)
    await callback_query.message.answer("✅ Ваше объявление отправлено на модерацию.")
    user_state[user_id] = None

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    if user_state.get(user_id) != "photo":
        return
    photo_file_id = message.photo[-1].file_id
    user_data[user_id]["photo"] = photo_file_id
    await submit_to_moderation(user_id)
    await message.answer("✅ Ваше объявление отправлено на модерацию.")
    user_state[user_id] = None

async def submit_to_moderation(user_id):
    data = user_data[user_id]
    caption = (
        f"🗂 Категория: {data['category']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 {data['text']}\n"
        f"📱 {data['contact']}"
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{user_id}")
    )
    # Сохраняем объявление со статусом "На модерации"
    user_posts.setdefault(user_id, []).append({
        "category": data['category'],
        "city": data['city'],
        "text": data['text'],
        "contact": data['contact'],
        "photo": data.get("photo"),
        "status": "На модерации"
    })
    if data.get("photo"):
        await bot.send_photo(MODERATOR_ID, data["photo"], caption=caption, reply_markup=kb)
    else:
        await bot.send_message(MODERATOR_ID, caption, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("decline_"))
async def handle_moderation(callback_query: types.CallbackQuery):
    action, user_id = callback_query.data.split("_")
    user_id = int(user_id)
    posts = user_posts.get(user_id)
    if not posts:
        await callback_query.answer("❌ Данные не найдены")
        return

    # Предполагаем, что последнее объявление - это то, которое модериуем
    data = posts[-1]
    caption = (
        f"🗂 Категория: {data['category']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 {data['text']}\n"
        f"📱 {data['contact']}"
    )
    if action == "approve":
        if data.get("photo"):
            await bot.send_photo(TARGET_CHANNEL, data["photo"], caption=caption)
        else:
            await bot.send_message(TARGET_CHANNEL, caption)
        # Обновляем статус
        data["status"] = "Опубликовано"
        await callback_query.answer("✅ Объявление опубликовано")
    else:
        data["status"] = "Отклонено"
        await callback_query.answer("❌ Объявление отклонено")
        await bot.send_message(user_id, "❌ Ваше объявление было отклонено модератором.")

@dp.callback_query_handler(lambda c: c.data == "cancel_post")
async def cancel_post(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_state[user_id] = None
    user_data.pop(user_id, None)
    await callback_query.message.answer("❌ Объявление отменено. Начните заново: /start")

@dp.callback_query_handler(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_state[user_id] = None
    user_data.pop(user_id, None)
    await callback_query.message.answer("🔙 Возвращаемся к выбору категории:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "my_posts")
async def my_posts(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    posts = user_posts.get(user_id)
    if not posts:
        await callback_query.message.answer("📋 У вас пока нет объявлений.")
        return

    text = "📋 Ваши объявления:\n\n"
    for i, post in enumerate(posts, 1):
        text += (
            f"{i}. Категория: {post['category']}\n"
            f"   Город: {post['city']}\n"
            f"   Текст: {post['text']}\n"
            f"   Контакт: {post['contact']}\n"
            f"   Статус: {post['status']}\n\n"
        )
    await callback_query.message.answer(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

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
