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
        'welcome': 'Добро пожаловать в официальный бот для отзывов "Iposuda"! �\n\nВыберите удобный язык общения:',
        'ask_name': 'Благодарим вас за выбор "Iposuda"! 🏆\n\nДля начала, пожалуйста, укажите ваше полное имя:',
        'ask_phone': 'Спасибо! 📱\n\nУкажите, пожалуйста, ваш контактный номер телефона в формате +7 (XXX) XXX-XX-XX:',
        'ask_birthday': 'Благодарим за предоставленные данные! �\n\nУкажите, пожалуйста, вашу дату рождения в формате ДД.ММ.ГГГГ:\n\n*Это поможет нам делать для вас специальные предложения в день рождения!',
        'consultant': 'Отлично! 👔\n\nУкажите, пожалуйста, имя консультанта, который вас обслуживал в "Iposuda":',
        'rate': 'Спасибо за информацию! ⭐\n\nОцените, пожалуйста, качество обслуживания консультанта {consultant} по шкале от 1 до 10, где 10 - наивысшая оценка:',
        'city': 'Благодарим за оценку! 🏙️\n\nУкажите, пожалуйста, ваш город:\n\n*Это помогает нам улучшать сервис в вашем регионе',
        'comment': 'Почти готово! ✍️\n\nНапишите, пожалуйста, ваш отзыв о посещении "Iposuda":\n\n- Что вам понравилось?\n- Что мы могли бы улучшить?',
        'thank_you': 'Искренне благодарим вас, {name}, за ваш отзыв! 💐\n\nВаше мнение очень важно для "Iposuda". Консультант {consultant} получит вашу оценку.\n\nЖдем вас снова в наших магазинах! При следующем посещении предъявите этот чат для получения специального предложения.'
    },
    'kz': {
        'welcome': '"Iposuda" ресмий пікірлер ботына қош келдіңіз! �\n\nСөйлесу тілін таңдаңыз:',
        'ask_name': '"Iposuda" таңдағаныңыз үшін рақмет! 🏆\n\nАты-жөніңізді көрсетіңіз:',
        'ask_phone': 'Рақмет! 📱\n\nБайланыс телефон нөміріңізді +7 (XXX) XXX-XX-XX форматында көрсетіңіз:',
        'ask_birthday': 'Ақпарат бергеніңіз үшін рақмет! 🎂\n\nТуған күніңізді КК.АА.ЖЖЖЖ форматында көрсетіңіз:\n\n*Бұл сізге туған күніңізде арнайы ұсыныстар жасауға көмектеседі!',
        'consultant': 'Тамаша! 👔\n\n"Iposuda" да қызмет көрсетген кеңесшінің аты-жөнін көрсетіңіз:',
        'rate': 'Ақпарат үшін рақмет! ⭐\n\n{consultant} кеңесшісінің қызмет сапасын 1-ден 10-ға дейін бағалаңыз, мұнда 10 - ең жоғары баға:',
        'city': 'Бағаңыз үшін рақмет! 🏙️\n\nҚалаңызды көрсетіңіз:\n\n*Бұл сіздің аймақтағы қызметті жақсартуға көмектеседі',
        'comment': 'Дайын болды! ✍️\n\n"Iposuda" сауда орталығына барғаныңыз туралы пікіріңізді жазыңыз:\n\n- Сізге не ұнады?\n- Біз неді жақсарта аламыз?',
        'thank_you': 'Пікіріңіз үшін шын жүректен алғыс білдіреміз, {name}! 💐\n\nСіздің пікіріңіз "Iposuda" үшін өте маңызды. {consultant} кеңесшісі сіздің бағаңызды алады.\n\nСізді қайтадан дүкендерімізде күтеміз! Келесі рет осы чатты арнайы ұсыныс алу үшін көрсетіңіз.'
    },
    'uz': {
        'welcome': '"Iposuda"ning rasmiy fikr-mulohazalar botiga xush kelibsiz! 🏏\n\nMuloqot tilini tanlang:',
        'ask_name': '"Iposuda"ni tanlaganingiz uchun tashakkur! 🏆\n\nToʻliq ismingizni kiriting:',
        'ask_phone': 'Rahmat! 📱\n\nIltimos, telefon raqamingizni +7 (XXX) XXX-XX-XX formatida kiriting:',
        'ask_birthday': 'Maʼlumot uchun tashakkur! 🎂\n\nTugʻilgan kuningizni KK.OY.YYYY formatida kiriting:\n\n*Bu sizga tugʻilgan kuningizda maxsus takliflar olishga yordam beradi!',
        'consultant': 'Ajoyib! 👔\n\n"Iposuda"da sizga xizmat koʻrsatgan maslahatchining ismini kiriting:',
        'rate': 'Maʼlumot uchun rahmat! ⭐\n\n{consultant} maslahatchisining xizmat sifatini 1 dan 10 gacha baholang, 10 eng yuqori baho:',
        'city': 'Baholaganingiz uchun tashakkur! 🏙️\n\nYashash shahringizni kiriting:\n\n*Bu bizga sizning mintaqangizda xizmatni yaxshilashga yordam beradi',
        'comment': 'Tayyor! ✍️\n\n"Iposuda"ga tashrifingiz haqida fikringizni yozing:\n\n- Sizga nima yoqdi?\n- Biz nimalarni yaxshilashimiz mumkin?',
        'thank_you': 'Fikringiz uchun chin qalbdan minnatdormiz, {name}! 💐\n\nSizning fikringiz "Iposuda" uchun juda muhim. {consultant} maslahatchisi sizning bahoyingizni oladi.\n\nSizni doʻkonlarimizda yana kutib qolamiz! Keyingi tashrifingizda maxsus taklif olish uchun ushbu chatni koʻrsating.'
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
    await message.answer(languages['ru']['welcome'], reply_markup=lang_keyboard)
    await state.set_state(Feedback.language)

@router.message(Feedback.language)
async def set_language(message: types.Message, state: FSMContext):
    lang = 'ru' if 'Рус' in message.text else 'kz' if 'Қаз' in message.text else 'uz' if 'O‘z' in message.text else ''
    if not lang:
        await message.answer("Пожалуйста, выберите язык из предложенных вариантов")
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
    text = languages[data['lang']]['consultant']
    await message.answer(text)
    await state.set_state(Feedback.consultant)

@router.message(Feedback.consultant)
async def get_consultant(message: types.Message, state: FSMContext):
    await state.update_data(consultant=message.text)
    data = await state.get_data()
    text = languages[data['lang']]['rate'].format(consultant=data['consultant'])
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
        f"📌 Новый отзыв для Iposuda\n"
        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👤 Клиент: {data['name']}\n"
        f"📞 Контакт: {data['phone']}\n"
        f"🎂 ДР: {data['birthday']}\n"
        f"🏙️ Город: {data['city']}\n"
        f"👨‍💼 Консультант: {data['consultant']}\n"
        f"⭐ Оценка: {data['rating']}/10\n"
        f"📝 Комментарий:\n{data['comment']}\n\n"
        f"#отзыв #iposuda"
    )

    thank = languages[data['lang']]['thank_you'].format(
        name=data['name'],
        consultant=data['consultant']
    )
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
                data['comment'], now, data.get('lang', 'ru')
            ])
        except Exception as e:
            print("Failed to write to Google Sheets:", e)

    await state.clear()

@router.message()
async def catch_all(message: types.Message):
    await message.answer("Благодарим за ваше сообщение! Для начала работы с ботом Iposuda отправьте команду /start")
