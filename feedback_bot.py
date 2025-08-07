import base64
import json
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# === Google Sheets Credentials ===
def load_credentials_from_env():
    credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not credentials_b64:
        raise Exception("GOOGLE_CREDENTIALS_BASE64 not set")
    credentials_json = base64.b64decode(credentials_b64).decode("utf-8")
    creds_dict = json.loads(credentials_json)
    return creds_dict

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
    print(f"Google Sheets error: {e}")
    sheet = None

# === FSM States ===
class Feedback(StatesGroup):
    language = State()
    name = State()
    phone = State()
    birthday = State()
    consultant = State()
    rating = State()
    city = State()
    comment = State()

# === Texts ===
languages = {
    'ru': {
        'ask_name': '👋 Как вас зовут?',
        'ask_phone': '📱 Укажите ваш номер телефона (например +7701...):',
        'ask_birthday': '🎂 Укажите вашу дату рождения (ДД.ММ.ГГГГ):',
        'consultant': '👤 {name}, кто вас консультировал?',
        'rate': '⭐ Оцените работу {consultant} от 1 до 10:',
        'city': '🏙️ Из какого вы города?',
        'comment': '💬 Ваш отзыв:',
        'thank_you': 'Спасибо, {name}! Отзыв сохранен. Консультант {consultant} получит уведомление.'
    },
    'kz': {
        'ask_name': '👋 Атыңыз кім?',
        'ask_phone': '📱 Телефон нөміріңізді енгізіңіз:',
        'ask_birthday': '🎂 Туған күніңіз (КК.АА.ЖЖЖЖ):',
        'consultant': '👤 {name}, сізге кім көмектесті?',
        'rate': '⭐ {consultant} жұмысын 1-10 аралығында бағалаңыз:',
        'city': '🏙️ Қай қаладансыз?',
        'comment': '💬 Пікіріңіз:',
        'thank_you': 'Рақмет, {name}! {consultant} туралы пікіріңіз сақталды.'
    },
    'uz': {
        'ask_name': '👋 Ismingiz nima?',
        'ask_phone': '📱 Telefon raqamingizni kiriting:',
        'ask_birthday': '🎂 Tug‘ilgan kuningiz (KK.OY.YYYY):',
        'consultant': '👤 {name}, kim sizga yordam berdi?',
        'rate': '⭐ {consultant} ishini 1 dan 10 gacha baholang:',
        'city': '🏙️ Qaysi shahardansiz?',
        'comment': '💬 Fikringiz:',
        'thank_you': 'Rahmat, {name}! {consultant} haqidagi fikringiz saqlandi.'
    }
}

lang_keyboard = ReplyKeyboardMarkup(keyboard=[[
    KeyboardButton(text="🇷🇺 Русский"),
    KeyboardButton(text="🇰🇿 Қазақша"),
    KeyboardButton(text="🇺🇿 O‘zbekcha")
]], resize_keyboard=True)

rating_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=str(i)) for i in range(1, 6)],
              [KeyboardButton(text=str(i)) for i in range(6, 11)]],
    resize_keyboard=True
)

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("🌍 Выберите язык:", reply_markup=lang_keyboard)
    await state.set_state(Feedback.language)

@router.message(Feedback.language)
async def set_language(message: types.Message, state: FSMContext):
    lang = 'ru' if 'Рус' in message.text else 'kz' if 'Қаз' in message.text else 'uz' if 'O‘z' in message.text else ''
    if not lang:
        await message.answer("Выберите язык из клавиатуры")
        return
    await state.update_data(lang=lang)
    await message.answer(languages[lang]['ask_name'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(Feedback.name)

@router.message(Feedback.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['ask_phone'])
    await state.set_state(Feedback.phone)

@router.message(Feedback.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['ask_birthday'])
    await state.set_state(Feedback.birthday)

@router.message(Feedback.birthday)
async def get_birthday(message: types.Message, state: FSMContext):
    await state.update_data(birthday=message.text)
    data = await state.get_data()
    text = languages[data['lang']]['consultant'].format(name=data['name'])
    await message.answer(text)
    await state.set_state(Feedback.consultant)

@router.message(Feedback.consultant)
async def get_consultant(message: types.Message, state: FSMContext):
    await state.update_data(consultant=message.text)
    data = await state.get_data()
    text = languages[data['lang']]['rate'].format(consultant=data['consultant'], name=data['name'])
    await message.answer(text, reply_markup=rating_keyboard)
    await state.set_state(Feedback.rating)

@router.message(Feedback.rating)
async def get_rating(message: types.Message, state: FSMContext):
    await state.update_data(rating=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['city'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(Feedback.city)

@router.message(Feedback.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    await message.answer(languages[data['lang']]['comment'])
    await state.set_state(Feedback.comment)

@router.message(Feedback.comment)
async def get_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    data = await state.get_data()

    summary = (
        f"📝 Новый отзыв:\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🎂 Дата рождения: {data['birthday']}\n"
        f"👨‍💼 Консультант: {data['consultant']}\n"
        f"⭐ Оценка: {data['rating']}\n"
        f"🏙️ Город: {data['city']}\n"
        f"💬 Комментарий: {data['comment']}"
    )

    thank = languages[data['lang']]['thank_you'].format(name=data['name'], consultant=data['consultant'])
    await message.answer(thank)

    try:
        await Bot(token=API_TOKEN).send_message(ADMIN_ID, summary)
    except Exception as e:
        print("Failed to send admin message:", e)

    if sheet:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([
                data['name'], data['phone'], data['birthday'],
                data['consultant'], data['rating'], data['city'],
                data['comment'], now
            ])
        except Exception as e:
            print("Failed to write to Google Sheets:", e)

    await state.clear()
@router.message()
async def catch_all(message: types.Message):
    print(f"📩 Получено сообщение от {message.from_user.id}: {message.text}")
    await message.answer(f"Принято сообщение: {message.text}")
