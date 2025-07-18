from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
)

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from aiogram import Bot, Dispatcher, executor, types
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токена бота из переменной окружения
API_TOKEN = os.getenv("YOUR_BOT_TOKEN")
ADMIN_ID = 884963545

if not API_TOKEN:
    raise ValueError("❌ Ошибка: переменная окружения 'YOUR_BOT_TOKEN' не задана")

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния FSM для подачи объявления
class PostAd(StatesGroup):
    Category = State()
    Description = State()
    Photo = State()
    Price = State()
    City = State()
    Contact = State()
    Confirm = State()

# Главное меню
main_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_kb.add(
    KeyboardButton("1️⃣ Работа"),
    KeyboardButton("2️⃣ Аренда жилья"),
    KeyboardButton("3️⃣ Продажа авто"),
    KeyboardButton("4️⃣ Мероприятия"),
)
main_menu_kb.add(
    KeyboardButton("5️⃣ Барахолка"),
    KeyboardButton("6️⃣ Даром"),
)
main_menu_kb.add(
    KeyboardButton("📤 Подать объявление"),
    KeyboardButton("📍 Выбрать город")
)

# Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для русскоязычных в Израиле 🇮🇱\n\nЧто вас интересует?",
        reply_markup=main_menu_kb
    )

# Обработка выбора подачи объявления
@dp.message_handler(lambda message: message.text == "📤 Подать объявление")
async def start_posting(message: types.Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Работа", "Аренда жилья")
    markup.add("Продажа авто", "Мероприятие")
    markup.add("Барахолка", "Даром")
    markup.add("🔙 Назад")

    await PostAd.Category.set()
    await message.answer("Что вы хотите разместить?", reply_markup=markup)

# Назад
@dp.message_handler(lambda message: message.text == "🔙 Назад", state="*")
async def go_back(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Вы вернулись в главное меню", reply_markup=main_menu_kb)

# Категория объявления
@dp.message_handler(state=PostAd.Category)
async def set_category(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await go_back(message, state)
        return
    await state.update_data(category=message.text)
    await PostAd.Description.set()
    await message.answer("Опишите ваше объявление:")

# Описание
@dp.message_handler(state=PostAd.Description)
async def set_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await PostAd.Photo.set()
    await message.answer("Пришлите фото или нажмите '🔙 Назад'")

# Фото
@dp.message_handler(content_types=['photo'], state=PostAd.Photo)
async def set_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await PostAd.Price.set()
    await message.answer("Укажите цену (если вещь отдаётся бесплатно, напишите 0):")

# Цена
@dp.message_handler(state=PostAd.Price)
async def set_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await PostAd.City.set()
    await message.answer("В каком городе находится вещь/объект?")

# Город
@dp.message_handler(state=PostAd.City)
async def set_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await PostAd.Contact.set()
    await message.answer("Оставьте контакт (номер или Telegram):")

# Контакт
@dp.message_handler(state=PostAd.Contact)
async def set_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    data = await state.get_data()

    text = (
        f"📬 Новое объявление:\n"
        f"📂 Категория: {data['category']}\n"
        f"📝 Описание: {data['description']}\n"
        f"🏙 Город: {data['city']}\n"
        f"💰 Цена: {data['price']}₪\n"
        f"📞 Контакт: {data['contact']}"
    )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Одобрить", callback_data="approve"),
        InlineKeyboardButton("❌ Отклонить", callback_data="reject")
    )

    await bot.send_photo(chat_id=ADMIN_ID, photo=data['photo'], caption=text, reply_markup=kb)
    await message.answer("✅ Ваше объявление отправлено на модерацию! Спасибо!")
    await state.finish()

# Хендлер для модерации
@dp.callback_query_handler(lambda c: c.data in ["approve", "reject"])
async def moderation_callback(call: types.CallbackQuery):
    if call.data == "approve":
        await call.message.edit_caption(call.message.caption + "\n\n✅ Объявление одобрено и опубликовано.")
        # Здесь можно добавить публикацию в канал или группу
    else:
        await call.message.edit_caption(call.message.caption + "\n\n❌ Объявление отклонено администратором.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
