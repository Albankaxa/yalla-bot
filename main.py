import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.utils.callback_data import CallbackData

API_TOKEN = os.getenv("YOUR_BOT_TOKEN")
ADMIN_ID = 884963545

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Модерация CallbackData
moderation_cb = CallbackData("mod", "action", "ad_id")

class Form(StatesGroup):
    category = State()
    city = State()
    title = State()
    description = State()
    price = State()
    contacts = State()
    photos = State()

ads = {}
user_ads = {}
ad_counter = 0

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add("Вакансии", "Продажа машин")
main_menu.add("Аренда жилья", "Мероприятия")
main_menu.add("Барахолка", "Даром")
main_menu.add("Подать объявление")

regions = {
    "Север": ["Хайфа", "Акко", "Нагария", "Цфат", "Тверия"],
    "Центр": ["Тель-Авив", "Нетания", "Петах-Тиква", "Рамат-Ган", "Холон"],
    "Юг": ["Беэр-Шева", "Ашдод", "Ашкелон", "Эйлат", "Кирьят-Гат"]
}

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в Yalla Bot 🇮🇱\nВыберите категорию:", reply_markup=main_menu)

@dp.message_handler(lambda message: message.text == "Подать объявление")
async def ad_create_start(message: types.Message, state: FSMContext):
    await Form.category.set()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in main_menu.keyboard:
        for button in row:
            if button.text != "Подать объявление":
                keyboard.add(button.text)
    keyboard.add("Назад")
    await message.answer("Выберите категорию объявления:", reply_markup=keyboard)

@dp.message_handler(state=Form.category)
async def select_category(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await cmd_start(message)
        return
    await state.update_data(category=message.text)
    await Form.next()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for region, cities in regions.items():
        keyboard.add(*cities)
    keyboard.add("Назад")
    await message.answer("Выберите город:", reply_markup=keyboard)

@dp.message_handler(state=Form.city)
async def select_city(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await Form.category.set()
        await ad_create_start(message, state)
        return
    await state.update_data(city=message.text)
    await Form.next()
    await message.answer("Введите заголовок объявления:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))

@dp.message_handler(state=Form.title)
async def enter_title(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await Form.city.set()
        await select_city(message, state)
        return
    await state.update_data(title=message.text)
    await Form.next()
    await message.answer("Введите описание:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))

@dp.message_handler(state=Form.description)
async def enter_description(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await Form.title.set()
        await enter_title(message, state)
        return
    await state.update_data(description=message.text)
    await Form.next()
    await message.answer("Введите цену:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))

@dp.message_handler(state=Form.price)
async def enter_price(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await Form.description.set()
        await enter_description(message, state)
        return
    await state.update_data(price=message.text)
    await Form.next()
    await message.answer("Укажите контакты (телефон, Telegram и т.п.):", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))

@dp.message_handler(state=Form.contacts)
async def enter_contacts(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await Form.price.set()
        await enter_price(message, state)
        return
    await state.update_data(contacts=message.text)
    await Form.next()
    await message.answer("Отправьте фото объявления (до 5 штук):")

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.photos)
async def receive_photos(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    if len(photos) >= 5:
        await finish_ad_creation(message, state)
    else:
        await message.answer("Фото получено. Можете отправить еще или введите /done, чтобы завершить.")

@dp.message_handler(commands=["done"], state=Form.photos)
async def finish_photo_upload(message: types.Message, state: FSMContext):
    await finish_ad_creation(message, state)

async def finish_ad_creation(message: types.Message, state: FSMContext):
    global ad_counter
    data = await state.get_data()
    ad_id = str(ad_counter)
    ad_counter += 1
    ads[ad_id] = data
    user_ads.setdefault(message.from_user.id, []).append(ad_id)
    await state.finish()

    media = [InputMediaPhoto(photo) for photo in data["photos"]]
    caption = f"<b>{data['title']}</b>\n📍 {data['city']}\n💰 {data['price']}\n📝 {data['description']}\n📞 {data['contacts']}"
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Одобрить", callback_data=moderation_cb.new(action="approve", ad_id=ad_id)),
        InlineKeyboardButton("❌ Отклонить", callback_data=moderation_cb.new(action="reject", ad_id=ad_id))
    )
    if len(media) == 1:
        await bot.send_photo(ADMIN_ID, photo=media[0].media, caption=caption, reply_markup=markup, parse_mode="HTML")
    else:
        media[0].caption = caption
        media[0].parse_mode = "HTML"
        await bot.send_media_group(ADMIN_ID, media=media)
        await bot.send_message(ADMIN_ID, "Выберите действие:", reply_markup=markup)

@dp.callback_query_handler(moderation_cb.filter())
async def moderation_action_handler(query: types.CallbackQuery, callback_data: dict):
    action = callback_data["action"]
    ad_id = callback_data["ad_id"]
    ad = ads.get(ad_id)
    if not ad:
        await query.answer("Объявление не найдено", show_alert=True)
        return

    if action == "approve":
        await bot.send_message(ad["contacts"], "Ваше объявление одобрено ✅")
        await query.answer("Одобрено")
    elif action == "reject":
        await bot.send_message(ad["contacts"], "Ваше объявление отклонено ❌")
        await query.answer("Отклонено")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
