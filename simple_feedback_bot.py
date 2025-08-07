# main.py

import asyncio
import base64
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# === Загрузка credentials из ENV ===
def load_credentials_from_env():
    credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not credentials_b64:
        raise Exception("Переменная GOOGLE_CREDENTIALS_BASE64 не найдена.")
    credentials_json = base64.b64decode(credentials_b64).decode("utf-8")
    creds_dict = json.loads(credentials_json)
    return creds_dict

# === Google Sheets Setup ===
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = load_credentials_from_env()
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1QTcOVKx6vC-f3NLolQVpbpKQsYDQOhdg8ozZpevUCeY/edit#gid=0"
try:
    sheet = client.open_by_url(SHEET_URL).sheet1
except Exception as e:
    print(f"Ошибка подключения к Google Sheets: {e}")
    sheet = None

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# === Состояния ===
class Feedback(StatesGroup):
    language = State()
    name = State()
    phone = State()
    birthday = State()
    consultant = State()
    rating = State()
    city = State()
    comment = State()


# === Языки ===
languages = {
    'ru': {
        'ask_name': '🍽️ Добро пожаловать в наш магазин посуды "Iposuda"! Как вас зовут?',
        'ask_phone': '📱 Укажите ваш номер телефона (например: +77012345678):',
        'ask_birthday': '🎂 Укажите вашу дату рождения (в формате ДД.ММ.ГГГГ):',
        'consultant': '👨‍💼 Отлично, {name}! Какой консультант вам помогал?',
        'rate': '⭐ {name}, как бы вы оценили работу консультанта {consultant}? (от 1 до 10)',
        'city': '🏙️ Из какого вы города?',
        'comment': '💭 Поделитесь вашим мнением о магазине:',
        'thank_you': '🙏 {name}, спасибо за отзыв! Мы передадим консультанту {consultant}.'
    },
    'kz': {
        'ask_name': '🍽️ "Iposuda" ыдыс дүкеніне қош келдіңіз! Сіздің атыңыз кім?',
        'ask_phone': '📱 Байланыс нөміріңізді жазыңыз (мысалы: +77012345678):',
        'ask_birthday': '🎂 Туған күніңізді жазыңыз (КК.АА.ЖЖЖЖ форматында):',
        'consultant': '👨‍💼 Жақсы, {name}! Қай кеңесші көмектесті?',
        'rate': '⭐ {name}, кеңесші {consultant} жұмысын 1-ден 10-ға дейін бағалаңыз:',
        'city': '🏙️ Қай қаладансыз?',
        'comment': '💭 Дүкен туралы пікіріңізбен бөлісіңіз:',
        'thank_you': '🙏 {name}, пікіріңізге рахмет! Біз {consultant} туралы мақтау айтамыз.'
    },
    'uz': {
        'ask_name': '🍽️ "Iposuda" do\'koniga xush kelibsiz! Ismingiz nima?',
        'ask_phone': '📱 Telefon raqamingizni yozing (masalan: +998901234567):',
        'ask_birthday': '🎂 Tug‘ilgan kuningizni yozing (KK.OY.YYYY formatida):',
        'consultant': '👨‍💼 Juda yaxshi, {name}! Qaysi konsultant yordam berdi?',
        'rate': '⭐ {name}, konsultant {consultant} ishini 1 dan 10 gacha baholang:',
        'city': '🏙️ Qaysi shahardansiz?',
        'comment': '💭 Do‘kon haqidagi fikringizni yozing:',
        'thank_you': '🙏 {name}, fikringiz uchun rahmat! {consultant}ga ma\'lumot beramiz.'
    },
}

lang_buttons = ReplyKeyboardMarkup(keyboard=[[
    KeyboardButton(text="🇷🇺 Русский"),
    KeyboardButton(text="🇰🇿 Қазақша"),
    KeyboardButton(text="🇺🇿 O‘zbekcha")
]], resize_keyboard=True)

rating_buttons = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=str(i)) for i in range(1, 6)],
              [KeyboardButton(text=str(i)) for i in range(6, 11)]],
    resize_keyboard=True)


# === /start ===
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    welcome_text = (
        "🍽️ Добро пожаловать в систему отзывов магазина посуды 'Iposuda'!\n\n"
        "🌍 Пожалуйста, выберите язык:")
    await message.answer(welcome_text, reply_markup=lang_buttons)
    await state.set_state(Feedback.language)


@dp.message(Feedback.language)
async def set_language(message: types.Message, state: FSMContext):
    lang = ''
    if "Рус" in message.text:
        lang = 'ru'
    elif "Қаз" in message.text:
        lang = 'kz'
    elif "O‘z" in message.text:
        lang = 'uz'
    else:
        await message.answer("Пожалуйста, выберите язык из списка.",
                             reply_markup=lang_buttons)
        return

    await state.update_data(lang=lang)
    await message.answer(languages[lang]['ask_name'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(Feedback.name)


@dp.message(Feedback.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['ask_phone'])
    await state.set_state(Feedback.phone)


@dp.message(Feedback.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['ask_birthday'])
    await state.set_state(Feedback.birthday)


@dp.message(Feedback.birthday)
async def get_birthday(message: types.Message, state: FSMContext):
    await state.update_data(birthday=message.text)
    data = await state.get_data()
    consultant_text = languages[data['lang']]['consultant'].format(name=data['name'])
    await message.answer(consultant_text)
    await state.set_state(Feedback.consultant)


@dp.message(Feedback.consultant)
async def get_consultant(message: types.Message, state: FSMContext):
    await state.update_data(consultant=message.text)
    data = await state.get_data()
    rating_text = languages[data['lang']]['rate'].format(
        name=data['name'], consultant=data['consultant'])
    await message.answer(rating_text, reply_markup=rating_buttons)
    await state.set_state(Feedback.rating)


@dp.message(Feedback.rating)
async def get_rating(message: types.Message, state: FSMContext):
    await state.update_data(rating=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['city'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(Feedback.city)


@dp.message(Feedback.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['comment'])
    await state.set_state(Feedback.comment)


@dp.message(Feedback.comment)
async def get_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    data = await state.get_data()

    summary = (f"📋 Новый отзыв:\n"
               f"👤 Имя: {data['name']}\n"
               f"📱 Телефон: {data['phone']}\n"
               f"🎂 Дата рождения: {data['birthday']}\n"
               f"👨‍💼 Консультант: {data['consultant']}\n"
               f"⭐ Оценка: {data['rating']}\n"
               f"🏙️ Город: {data['city']}\n"
               f"💬 Комментарий: {data['comment']}")

    thank_you_text = languages[data['lang']]['thank_you'].format(
        name=data['name'], consultant=data['consultant'])
    await message.answer(thank_you_text)
    await bot.send_message(ADMIN_ID, summary)

    # Google Sheets
    if sheet:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([
                data['name'], data['phone'], data['birthday'],
                data['consultant'], data['rating'], data['city'],
                data['comment'], now
            ])
        except Exception as e:
            print(f"Ошибка записи в Google Sheets: {e}")
    else:
        print("Google Sheets недоступен, данные не сохранены")

    await state.clear()


# === Запуск ===
async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
