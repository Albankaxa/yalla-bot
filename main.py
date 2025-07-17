import os
import logging
import sqlite3
import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Command
from collections import defaultdict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = os.getenv("YOUR_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("❌ Ошибка: переменная окружения 'YOUR_BOT_TOKEN' не задана.")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

MODERATOR_ID = 884963545
TARGET_CHANNEL = "@yallaisrael"
SPAM_LIMIT = 3  # максимум объявлений в день
SPAM_WINDOW = 24 * 60 * 60  # 24 часа в секундах

# Хранение состояний
user_state = {}
user_data = {}
user_lang = defaultdict(lambda: "ru")

# Конфигурация категорий и городов
categories = {
    "work": {"ru": "👷 Работа", "en": "👷 Work", "he": "👷 עבודה"},
    "rent": {"ru": "🏠 Аренда жилья", "en": "🏠 Housing Rent", "he": "🏠 השכרת דיור"},
    "car": {"ru": "🚗 Продажа авто", "en": "🚗 Car Sales", "he": "🚗 מכירת רכב"},
    "event": {"ru": "🎭 Мероприятия", "en": "🎭 Events", "he": "🎭 אירועים"},
    "sell": {"ru": "📦 Барахолка", "en": "📦 Marketplace", "he": "📦 מכירות"},
    "free": {"ru": "🎁 Даром", "en": "🎁 Free", "he": "🎁 בחינם"}
}

CITIES = [
    "Тель-Авив", "Хайфа", "Иерусалим", "Беэр-Шева", "Ашдод", "Нетивот",
    "Ришон-ле-Цион", "Эйлат", "Холон", "Бат-Ям"
]

LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇺🇸 English", 
    "he": "🇮🇱 עברית"
}

# Переводы
TRANSLATIONS = {
    "ru": {
        "welcome": "👋 Добро пожаловать в Yalla Bot!\nВыберите категорию:",
        "help": "Чтобы опубликовать объявление, нажмите /start и следуйте инструкциям.",
        "my_posts": "📋 Мои объявления",
        "language": "🌐 Язык",
        "share_bot": "📢 Поделиться ботом",
        "search": "🔍 Поиск",
        "back": "🔙 Назад",
        "choose_city": "🌆 Выберите город:",
        "enter_text": "✏️ Введите текст объявления:",
        "enter_contact": "📞 Введите контакт (номер телефона или @username):",
        "add_photo": "Добавьте фото или пропустите:",
        "upload_photo": "📷 Загрузить фото",
        "skip_photo": "⏭ Без фото",
        "send_photo": "📸 Пришлите фото:",
        "moderation_sent": "✅ Объявление отправлено на модерацию",
        "session_expired": "⚠️ Сессия устарела. Нажмите /start",
        "no_posts": "📭 У вас пока нет объявлений",
        "your_posts": "📋 Ваши объявления:",
        "status": "📌 Статус:",
        "pending": "На модерации",
        "published": "Опубликовано",
        "rejected": "Отклонено",
        "expired": "Истекло",
        "post_rejected": "❌ Ваше объявление было отклонено",
        "access_denied": "⛔ Доступ запрещён",
        "language_set": "✅ Язык установлен:",
        "choose_language": "🌐 Выберите язык:",
        "spam_limit": "⚠️ Превышен лимит объявлений. Попробуйте завтра.",
        "invalid_contact": "❌ Неверный формат контакта. Используйте номер телефона или @username",
        "edit_post": "✏️ Редактировать",
        "delete_post": "🗑 Удалить",
        "post_deleted": "✅ Объявление удалено",
        "choose_post_to_edit": "Выберите объявление для редактирования:",
        "edit_text": "📝 Изменить текст",
        "edit_contact": "📞 Изменить контакт",
        "edit_photo": "📷 Изменить фото",
        "save_changes": "💾 Сохранить изменения",
        "changes_saved": "✅ Изменения сохранены",
        "search_category": "🔍 Выберите категорию для поиска:",
        "search_city": "🏙 Выберите город:",
        "search_results": "🔍 Результаты поиска:",
        "no_results": "❌ Объявления не найдены",
        "post_expired_notification": "⏰ Ваше объявление истекло и было удалено из канала",
        "approve": "✅ Одобрить",
        "decline": "❌ Отклонить",
        "approved": "✅ Опубликовано",
        "declined": "❌ Отклонено",
        "new_text": "Введите новый текст:",
        "new_contact": "Введите новый контакт:",
        "new_photo": "Пришлите новое фото:",
        "cancel": "❌ Отмена"
    },
    "en": {
        "welcome": "👋 Welcome to Yalla Bot!\nSelect a category:",
        "help": "To publish an ad, press /start and follow the instructions.",
        "my_posts": "📋 My Posts",
        "language": "🌐 Language",
        "share_bot": "📢 Share Bot",
        "search": "🔍 Search",
        "back": "🔙 Back",
        "choose_city": "🌆 Choose city:",
        "enter_text": "✏️ Enter ad text:",
        "enter_contact": "📞 Enter contact (phone number or @username):",
        "add_photo": "Add photo or skip:",
        "upload_photo": "📷 Upload Photo",
        "skip_photo": "⏭ No Photo",
        "send_photo": "📸 Send photo:",
        "moderation_sent": "✅ Ad sent for moderation",
        "session_expired": "⚠️ Session expired. Press /start",
        "no_posts": "📭 You have no ads yet",
        "your_posts": "📋 Your ads:",
        "status": "📌 Status:",
        "pending": "Under moderation",
        "published": "Published",
        "rejected": "Rejected",
        "expired": "Expired",
        "post_rejected": "❌ Your ad was rejected",
        "access_denied": "⛔ Access denied",
        "language_set": "✅ Language set:",
        "choose_language": "🌐 Choose language:",
        "spam_limit": "⚠️ Ad limit exceeded. Try tomorrow.",
        "invalid_contact": "❌ Invalid contact format. Use phone number or @username",
        "edit_post": "✏️ Edit",
        "delete_post": "🗑 Delete",
        "post_deleted": "✅ Ad deleted",
        "choose_post_to_edit": "Choose ad to edit:",
        "edit_text": "📝 Edit text",
        "edit_contact": "📞 Edit contact",
        "edit_photo": "📷 Edit photo",
        "save_changes": "💾 Save changes",
        "changes_saved": "✅ Changes saved",
        "search_category": "🔍 Select category to search:",
        "search_city": "🏙 Select city:",
        "search_results": "🔍 Search results:",
        "no_results": "❌ No ads found",
        "post_expired_notification": "⏰ Your ad has expired and was removed from the channel",
        "approve": "✅ Approve",
        "decline": "❌ Decline",
        "approved": "✅ Published",
        "declined": "❌ Declined",
        "new_text": "Enter new text:",
        "new_contact": "Enter new contact:",
        "new_photo": "Send new photo:",
        "cancel": "❌ Cancel"
    },
    "he": {
        "welcome": "👋 ברוכים הבאים ל-Yalla Bot!\nבחרו קטגוריה:",
        "help": "כדי לפרסם מודעה, לחצו /start ועקבו אחר ההוראות.",
        "my_posts": "📋 המודעות שלי",
        "language": "🌐 שפה",
        "share_bot": "📢 שתף בוט",
        "search": "🔍 חיפוש",
        "back": "🔙 חזור",
        "choose_city": "🌆 בחרו עיר:",
        "enter_text": "✏️ הכניסו טקסט מודעה:",
        "enter_contact": "📞 הכניסו איש קשר (מספר טלפון או @username):",
        "add_photo": "הוסיפו תמונה או דלגו:",
        "upload_photo": "📷 העלו תמונה",
        "skip_photo": "⏭ בלי תמונה",
        "send_photo": "📸 שלחו תמונה:",
        "moderation_sent": "✅ המודעה נשלחה לאישור",
        "session_expired": "⚠️ הסשן פג. לחצו /start",
        "no_posts": "📭 אין לכם מודעות עדיין",
        "your_posts": "📋 המודעות שלכם:",
        "status": "📌 סטטוס:",
        "pending": "בבדיקה",
        "published": "פורסם",
        "rejected": "נדחה",
        "expired": "פג",
        "post_rejected": "❌ המודעה שלכם נדחתה",
        "access_denied": "⛔ גישה נדחתה",
        "language_set": "✅ השפה נקבעה:",
        "choose_language": "🌐 בחרו שפה:",
        "spam_limit": "⚠️ חרגתם ממגבלת המודעות. נסו מחר.",
        "invalid_contact": "❌ פורמט איש קשר שגוי. השתמשו במספר טלפון או @username",
        "edit_post": "✏️ ערוך",
        "delete_post": "🗑 מחק",
        "post_deleted": "✅ המודעה נמחקה",
        "choose_post_to_edit": "בחרו מודעה לעריכה:",
        "edit_text": "📝 ערוך טקסט",
        "edit_contact": "📞 ערוך איש קשר",
        "edit_photo": "📷 ערוך תמונה",
        "save_changes": "💾 שמור שינויים",
        "changes_saved": "✅ השינויים נשמרו",
        "search_category": "🔍 בחרו קטגוריה לחיפוש:",
        "search_city": "🏙 בחרו עיר:",
        "search_results": "🔍 תוצאות חיפוש:",
        "no_results": "❌ לא נמצאו מודעות",
        "post_expired_notification": "⏰ המודעה שלכם פגה והוסרה מהערוץ",
        "approve": "✅ אשר",
        "decline": "❌ דחה",
        "approved": "✅ פורסם",
        "declined": "❌ נדחה",
        "new_text": "הכניסו טקסט חדש:",
        "new_contact": "הכניסו איש קשר חדש:",
        "new_photo": "שלחו תמונה חדשה:",
        "cancel": "❌ בטל"
    }
}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        language TEXT DEFAULT 'ru',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица объявлений
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        city TEXT,
        text TEXT,
        contact TEXT,
        photo_id TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Таблица статистики
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

# Функции для работы с базой данных
def get_user_language(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT language FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'ru'

def save_user(user_id, username, first_name, language='ru'):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users (id, username, first_name, language, last_activity)
                 VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''', 
              (user_id, username, first_name, language))
    conn.commit()
    conn.close()

def update_user_language(user_id, language):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET language = ? WHERE id = ?', (language, user_id))
    conn.commit()
    conn.close()

def save_post(user_id, category, city, text, contact, photo_id=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    c.execute('''INSERT INTO posts (user_id, category, city, text, contact, photo_id, expires_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, category, city, text, contact, photo_id, expires_at))
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    return post_id

def get_user_posts(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''SELECT id, category, city, text, contact, photo_id, status, created_at
                 FROM posts WHERE user_id = ? ORDER BY created_at DESC''', (user_id,))
    posts = c.fetchall()
    conn.close()
    return posts

def update_post_status(post_id, status):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('UPDATE posts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
              (status, post_id))
    conn.commit()
    conn.close()

def delete_post(post_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

def get_post_by_id(post_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = c.fetchone()
    conn.close()
    return post

def update_post(post_id, text=None, contact=None, photo_id=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    updates = []
    values = []
    
    if text is not None:
        updates.append('text = ?')
        values.append(text)
    if contact is not None:
        updates.append('contact = ?')
        values.append(contact)
    if photo_id is not None:
        updates.append('photo_id = ?')
        values.append(photo_id)
    
    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        values.append(post_id)
        
        query = f'UPDATE posts SET {", ".join(updates)} WHERE id = ?'
        c.execute(query, values)
        conn.commit()
    
    conn.close()

def search_posts(category=None, city=None, limit=10):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    query = 'SELECT * FROM posts WHERE status = "published"'
    params = []
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if city:
        query += ' AND city = ?'
        params.append(city)
    
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    posts = c.fetchall()
    conn.close()
    return posts

def check_spam_limit(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''SELECT COUNT(*) FROM posts 
                 WHERE user_id = ? AND created_at > datetime('now', '-24 hours')''',
              (user_id,))
    count = c.fetchone()[0]
    conn.close()
    
    return count >= SPAM_LIMIT

def get_stats():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM posts')
    total_posts = c.fetchone()[0]
    
    c.execute('SELECT status, COUNT(*) FROM posts GROUP BY status')
    status_counts = dict(c.fetchall())
    
    c.execute('''SELECT COUNT(*) FROM users 
                 WHERE last_activity > datetime('now', '-24 hours')''')
    active_users = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_posts': total_posts,
        'status_counts': status_counts,
        'active_users': active_users
    }

def validate_contact(contact):
    phone_pattern = r'^(\+?[1-9]\d{1,14}|\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4,6})$'
    username_pattern = r'^@[a-zA-Z0-9_]{5,32}$'
    
    return bool(re.match(phone_pattern, contact) or re.match(username_pattern, contact))

# Функции для создания клавиатур
def get_text(user_id, key):
    lang = get_user_language(user_id)
    return TRANSLATIONS[lang].get(key, key)

def main_menu(user_id):
    lang = get_user_language(user_id)
    kb = InlineKeyboardMarkup(row_width=2)
    
    for key, translations in categories.items():
        kb.insert(InlineKeyboardButton(translations[lang], callback_data=f"cat_{key}"))
    
    kb.add(InlineKeyboardButton(get_text(user_id, "my_posts"), callback_data="my_posts"))
    kb.add(InlineKeyboardButton(get_text(user_id, "search"), callback_data="search"))
    kb.add(InlineKeyboardButton(get_text(user_id, "language"), callback_data="change_lang"))
    kb.add(InlineKeyboardButton(get_text(user_id, "share_bot"), switch_inline_query=""))
    
    return kb

def city_menu(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    for city in CITIES:
        kb.insert(InlineKeyboardButton(city, callback_data=f"city_{city}"))
    kb.add(InlineKeyboardButton(get_text(user_id, "back"), callback_data="back_to_categories"))
    return kb

def lang_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for code, name in LANGUAGES.items():
        kb.insert(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
    return kb

def search_category_menu(user_id):
    lang = get_user_language(user_id)
    kb = InlineKeyboardMarkup(row_width=2)
    
    for key, translations in categories.items():
        kb.insert(InlineKeyboardButton(translations[lang], callback_data=f"search_cat_{key}"))
    
    kb.add(InlineKeyboardButton(get_text(user_id, "back"), callback_data="back_to_main"))
    return kb

def search_city_menu(user_id, category):
    kb = InlineKeyboardMarkup(row_width=2)
    for city in CITIES:
        kb.insert(InlineKeyboardButton(city, callback_data=f"search_city_{category}_{city}"))
    kb.add(InlineKeyboardButton(get_text(user_id, "back"), callback_data="search"))
    return kb

def post_actions_menu(user_id, post_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(get_text(user_id, "edit_post"), callback_data=f"edit_{post_id}"),
        InlineKeyboardButton(get_text(user_id, "delete_post"), callback_data=f"delete_{post_id}")
    )
    kb.add(InlineKeyboardButton(get_text(user_id, "back"), callback_data="my_posts"))
    return kb

def edit_menu(user_id, post_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(get_text(user_id, "edit_text"), callback_data=f"edit_text_{post_id}"),
        InlineKeyboardButton(get_text(user_id, "edit_contact"), callback_data=f"edit_contact_{post_id}")
    )
    kb.add(InlineKeyboardButton(get_text(user_id, "edit_photo"), callback_data=f"edit_photo_{post_id}"))
    kb.add(InlineKeyboardButton(get_text(user_id, "back"), callback_data=f"post_{post_id}"))
    return kb

# Обработчики команд
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    save_user(user_id, message.from_user.username, message.from_user.first_name)
    
    await message.answer(
        get_text(user_id, "welcome"),
        reply_markup=main_menu(user_id)
    )

@dp.message_handler(commands=["help"])
async def help_command(message: types.Message):
    user_id = message.from_user.id
    await message.answer(get_text(user_id, "help"))

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if message.from_user.id != MODERATOR_ID:
        await message.answer(get_text(message.from_user.id, "access_denied"))
        return
    
    stats = get_stats()
    
    stats_text = f"""📊 Статистика бота:
    
👥 Всего пользователей: {stats['total_users']}
📱 Активных за 24ч: {stats['active_users']}
📋 Всего объявлений: {stats['total_posts']}

📌 По статусам:
• На модерации: {stats['status_counts'].get('pending', 0)}
• Опубликовано: {stats['status_counts'].get('published', 0)}
• Отклонено: {stats['status_counts'].get('rejected', 0)}
• Истекло: {stats['status_counts'].get('expired', 0)}"""
    
    await message.answer(stats_text)

# Обработчики callback-запросов
@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    lang = callback_query.data[5:]
    
    update_user_language(user_id, lang)
    user_lang[user_id] = lang
    
    await callback_query.message.edit_text(
        f"{get_text(user_id, 'language_set')} {LANGUAGES[lang]}",
        reply_markup=main_menu(user_id)
    )

@dp.callback_query_handler(lambda c: c.data == "change_lang")
async def change_language(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.edit_text(
        get_text(user_id, "choose_language"),
        reply_markup=lang_menu()
    )

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def choose_category(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if check_spam_limit(user_id):
        await callback_query.answer(get_text(user_id, "spam_limit"))
        return
    
    cat = callback_query.data[4:]
    lang = get_user_language(user_id)
    
    user_data[user_id] = {"category": cat, "category_display": categories[cat][lang]}
    user_state[user_id] = "city"
    
    await callback_query.message.edit_text(
        get_text(user_id, "choose_city"),
        reply_markup=city_menu(user_id)
    )

@dp.callback_query_handler(lambda c: c.data.startswith("city_"))
async def choose_city(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = callback_query.data[5:]
    
    if user_id not in user_data:
        await callback_query.message.edit_text(get_text(user_id, "session_expired"))
        return
    
    user_data[user_id]["city"] = city
    user_state[user_id] = "text"
    
    await callback_query.message.edit_text(get_text(user_id, "enter_text"))

@dp.callback_query_handler(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.edit_text(
        get_text(user_id, "welcome"),
        reply_markup=main_menu(user_id)
    )

@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.edit_text(
        get_text(user_id, "welcome"),
        reply_markup=main_menu(user_id)
    )

# Обработчики ввода текста
@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "text")
async def enter_text(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["text"] = message.text
    user_state[user_id] = "contact"
    await message.answer(get_text(user_id, "enter_contact"))

@dp.message_handler(lambda message: user_state.get(message.from_user.id) == "contact")
async def enter_contact(message: types.Message):