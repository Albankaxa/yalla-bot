import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

API_TOKEN = os.getenv("YOUR_BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("❌ Не задан YOUR_BOT_TOKEN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- Данные ---

CATEGORIES = [
    "🏢 Работа",
    "🏠 Аренда жилья",
    "🚗 Продажа авто",
    "🎉 Мероприятия",
    "🛒 Барахолка",
    "🎁 Даром"
]

CITIES = {
    "Север": ["Хайфа", "Нагария", "Акко", "Кармиэль", "Цфат", "Назарет", "Ацмон", "Маалот", "Кацрин", "Тверия"],
    "Центр": ["Тель-Авив", "Нетания", "Герцлия", "Бат-Ям", "Холон", "Рамат-Ган", "Петах-Тиква", "Ришон-ле-Цион", "Бней-Брак", "Раанана"],
    "Юг": ["Беэр-Шева", "Ашдод", "Ашкелон", "Эйлат", "Кирьят-Гат", "Сдерот", "Мицпе-Рамон", "Димона", "Офаким", "Нетивот"]
}

# Хранилище объявлений в формате:
# { user_id: [ {category, city, description, photos:list(file_id)} ] }
user_ads = {}

# --- Клавиатуры ---

def main_menu_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить объявление")
    kb.add("👤 Мои объявления")
    return kb

def categories_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cat in CATEGORIES:
        kb.add(cat)
    kb.add("❌ Отмена")
    return kb

def cities_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for region, cities in CITIES.items():
        kb.add(f"⬇️ {region}")
        for city in cities:
            kb.add(city)
    kb.add("❌ Отмена")
    return kb

def back_to_main_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("🔙 Главное меню")
    return kb

# --- FSM States ---

class AdForm(StatesGroup):
    waiting_for_category = State()
    waiting_for_city = State()
    waiting_for_description = State()
    waiting_for_photos = State()
    confirm = State()

# --- Хендлеры ---

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу разместить твои объявления.\n\n"
        "Выбери действие:",
        reply_markup=main_menu_kb()
    )

@dp.message_handler(lambda msg: msg.text == "➕ Добавить объявление")
async def add_ad_start(message: types.Message):
    await message.answer("Выберите категорию объявления:", reply_markup=categories_kb())
    await AdForm.waiting_for_category.set()

@dp.message_handler(state=AdForm.waiting_for_category)
async def ad_category_chosen(message: types.Message, state: FSMContext):
    if message.text not in CATEGORIES:
        await message.answer("Пожалуйста, выберите категорию из списка или отмените.")
        return
    await state.update_data(category=message.text)
    # Отправляем города (разделяем регионы)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for region, cities in CITIES.items():
        kb.add(f"⬇️ {region}")
        for city in cities:
            kb.add(city)
    kb.add("❌ Отмена")
    await message.answer("Теперь выберите город:", reply_markup=kb)
    await AdForm.waiting_for_city.set()

@dp.message_handler(state=AdForm.waiting_for_city)
async def ad_city_chosen(message: types.Message, state: FSMContext):
    all_cities = sum(CITIES.values(), [])
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Добавление объявления отменено.", reply_markup=main_menu_kb())
        return
    if message.text not in all_cities:
        await message.answer("Пожалуйста, выберите город из списка или отмените.")
        return
    await state.update_data(city=message.text)
    await message.answer("Опишите ваше объявление (текст, до 1000 символов):", reply_markup=ReplyKeyboardRemove())
    await AdForm.waiting_for_description.set()

@dp.message_handler(state=AdForm.waiting_for_description, content_types=types.ContentTypes.TEXT)
async def ad_description_received(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > 1000:
        await message.answer("Слишком длинное описание, пожалуйста, сократите до 1000 символов.")
        return
    await state.update_data(description=text)
    await message.answer(
        "Теперь отправьте фото для объявления (можно до 5 штук).\n"
        "Отправьте /done, когда закончите добавлять фото.\n"
        "Если фото не нужны — сразу отправьте /done.",
        reply_markup=back_to_main_kb()
    )
    await AdForm.waiting_for_photos.set()

@dp.message_handler(state=AdForm.waiting_for_photos, content_types=[types.ContentType.PHOTO, types.ContentType.TEXT])
async def ad_photos_handler(message: types.Message, state: FSMContext):
    if message.text == "/done":
        data = await state.get_data()
        category = data['category']
        city = data['city']
        description = data['description']
        photos = data.get('photos', [])
        user_id = message.from_user.id

        # Сохраняем объявление
        ad = {
            "category": category,
            "city": city,
            "description": description,
            "photos": photos
        }
        user_ads.setdefault(user_id, []).append(ad)
        await message.answer("✅ Ваше объявление опубликовано!", reply_markup=main_menu_kb())
        await state.finish()
        return

    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        data = await state.get_data()
        photos = data.get("photos", [])
        if len(photos) >= 5:
            await message.answer("⚠️ Можно добавить не более 5 фото.")
            return
        photos.append(file_id)
        await state.update_data(photos=photos)
        await message.answer(f"Фото принято ({len(photos)}/5). Отправьте ещё или /done для окончания.")
    else:
        await message.answer("Пожалуйста, отправьте фото или команду /done.")

@dp.message_handler(lambda msg: msg.text == "👤 Мои объявления")
async def show_my_ads(message: types.Message):
    user_id = message.from_user.id
    ads = user_ads.get(user_id)
    if not ads:
        await message.answer("У вас нет опубликованных объявлений.", reply_markup=main_menu_kb())
        return
    for i, ad in enumerate(ads, 1):
        text = (
            f"📌 Объявление #{i}\n"
            f"Категория: {ad['category']}\n"
            f"Город: {ad['city']}\n"
            f"Описание: {ad['description']}"
        )
        if ad['photos']:
            media = [types.InputMediaPhoto(file_id) for file_id in ad['photos']]
            await message.answer_media_group(media)
        await message.answer(text)
    await message.answer("Это все ваши объявления.", reply_markup=main_menu_kb())

@dp.message_handler(lambda msg: msg.text == "🔙 Главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Возврат в главное меню.", reply_markup=main_menu_kb())

@dp.message_handler()
async def fallback(message: types.Message):
    await message.answer("Пожалуйста, используйте меню ниже.", reply_markup=main_menu_kb())

if __name__ == "__main__":
    logger.info("Запуск бота")
    executor.start_polling(dp, skip_updates=True)
