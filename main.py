from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text
import logging
import os
import asyncio

API_TOKEN = os.getenv("YOUR_BOT_TOKEN")
ADMIN_ID = 884963545

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- FSM ---
class Form(StatesGroup):
    choosing_category = State()
    choosing_city = State()
    choosing_price_range = State()
    showing_ads = State()
    filtering_ads = State()
    submitting_ad = State()
    awaiting_moderation = State()

# --- Кнопки ---
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("1️⃣ Работа", "2️⃣ Аренда жилья")
    kb.add("3️⃣ Продажа авто", "4️⃣ Мероприятия")
    kb.add("📦 Барахолка", "🎁 Даром")
    kb.add("📤 Подать объявление", "📍 Выбрать город")
    return kb

def city_menu():
    cities = ["Тель-Авив", "Хайфа", "Ашдод", "Бат-Ям", "Нетания", "Иерусалим", "Ашкелон", "Беэр-Шева", "Ришон-ле-Цион", "Петах-Тиква"]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(0, len(cities), 2):
        kb.add(cities[i], cities[i+1] if i+1 < len(cities) else "")
    kb.add("⬅️ Назад")
    return kb

def price_menu(category):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if category == "2️⃣ Аренда жилья":
        kb.add("До 3000₪", "3000–5000₪", "5000₪ и выше", "Не важно")
    elif category == "3️⃣ Продажа авто":
        kb.add("До 10,000₪", "10,000–20,000₪", "20,000–30,000₪", "30,000₪ и выше", "Не важно")
    elif category == "📦 Барахолка":
        kb.add("До 100₪", "100–500₪", "500–1000₪", "1000₪ и выше", "Не важно")
    return kb

def filter_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔍 Поиск по ключевым словам", "🕒 Сортировать по дате")
    kb.add("💸 Сортировать по цене", "📄 Показать все объявления")
    kb.add("⬅️ Назад")
    return kb

def ads_navigation_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Показать еще")
    kb.add("⬅️ Назад")
    return kb

def moderation_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Одобрить", callback_data="approve"))
    kb.add(InlineKeyboardButton("❌ Отклонить", callback_data="reject"))
    return kb

# --- Команды ---
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Привет! Я бот для русскоязычных в Израиле 🇮🇱\nЧто вас интересует?", reply_markup=main_menu())

# --- Выбор категории ---
@dp.message_handler(lambda m: m.text in ["1️⃣ Работа", "2️⃣ Аренда жилья", "3️⃣ Продажа авто", "4️⃣ Мероприятия", "📦 Барахолка", "🎁 Даром"])
async def category_chosen(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await Form.choosing_city.set()
    await message.answer("📍 Выберите город:", reply_markup=city_menu())

# --- Выбор города ---
@dp.message_handler(lambda m: m.text in ["Тель-Авив", "Хайфа", "Ашдод", "Бат-Ям", "Нетания", "Иерусалим", "Ашкелон", "Беэр-Шева", "Ришон-ле-Цион", "Петах-Тиква"], state=Form.choosing_city)
async def city_chosen(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    await state.update_data(city=message.text)
    category = user_data['category']
    if category in ["2️⃣ Аренда жилья", "3️⃣ Продажа авто", "📦 Барахолка"]:
        await Form.choosing_price_range.set()
        await message.answer("💰 Выберите диапазон цен:", reply_markup=price_menu(category))
    else:
        await Form.showing_ads.set()
        await message.answer(f"🔍 Показываю объявления: {category} в {message.text}\n(Без фильтра по цене)", reply_markup=filter_menu())

# --- Выбор ценового диапазона ---
@dp.message_handler(state=Form.choosing_price_range)
async def price_range_chosen(message: types.Message, state: FSMContext):
    await state.update_data(price_range=message.text)
    data = await state.get_data()
    await Form.showing_ads.set()
    await message.answer(f"🔍 Показываю объявления: {data['category']} в {data['city']} по цене: {data['price_range']}", reply_markup=filter_menu())

# --- Отображение фильтров ---
@dp.message_handler(lambda m: m.text.startswith("🔍") or m.text.startswith("🕒") or m.text.startswith("💸") or m.text.startswith("📄"), state=Form.showing_ads)
async def handle_filters(message: types.Message, state: FSMContext):
    await message.answer("📢 [Заглушка] Здесь будут показаны отфильтрованные объявления.", reply_markup=ads_navigation_menu())

# --- Подать объявление ---
@dp.message_handler(lambda m: m.text == "📤 Подать объявление")
async def submit_ad_start(message: types.Message, state: FSMContext):
    await Form.choosing_category.set()
    await message.answer("📝 Выберите категорию объявления:", reply_markup=main_menu())

# --- Назад ---
@dp.message_handler(lambda m: m.text == "⬅️ Назад", state="*")
async def go_back(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current == Form.choosing_price_range.state:
        await Form.choosing_city.set()
        await message.answer("📍 Вернитесь к выбору города:", reply_markup=city_menu())
    elif current == Form.choosing_city.state:
        await Form.choosing_category.set()
        await message.answer("🔙 Выберите категорию:", reply_markup=main_menu())
    elif current == Form.showing_ads.state:
        await Form.choosing_price_range.set()
        user_data = await state.get_data()
        await message.answer("💰 Вернитесь к выбору цены:", reply_markup=price_menu(user_data['category']))
    else:
        await message.answer("🔙 Возврат невозможен")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
