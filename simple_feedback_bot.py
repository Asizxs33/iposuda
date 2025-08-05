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

# [Остальной код остается без изменений]


# === Состояния ===
class Feedback(StatesGroup):
    language = State()
    name = State()
    consultant = State()
    rating = State()
    city = State()
    comment = State()


# === Языки ===
languages = {
    'ru': {
        'ask_name':
        '🍽️ Добро пожаловать в наш магазин посуды "Iposuda"!\n\n👋 Мы очень ценим каждого покупателя и хотим улучшать качество нашего сервиса. Ваше мнение невероятно важно для нас!\n\nДавайте знакомиться! Как вас зовут?',
        'consultant':
        '👨‍💼 Отлично, {name}! Спасибо, что выбрали наш магазин для покупки кухонной посуды.\n\nРасскажите, пожалуйста, какой консультант помогал вам с выбором товара? (Напишите имя или опишите сотрудника)\n\nЭто поможет нам отметить лучших специалистов! 🏆',
        'rate':
        '⭐ {name}, мы будем очень благодарны за вашу честную оценку работы консультанта {consultant}.\n\nОн помог вам:\n• Найти подходящую посуду?\n• Рассказал о характеристиках товаров?\n• Был вежлив и профессионален?\n\nОцените его работу от 1 до 10, где:\n1-3 = неудовлетворительно 😞\n4-6 = удовлетворительно 😐\n7-8 = хорошо 😊\n9-10 = отлично! 🌟',
        'city':
        '🏙️ Прекрасно! А из какого вы города? Это поможет нам понять географию наших покупателей и возможно открыть новые точки продаж в вашем регионе! 📍',
        'comment':
        '💭 И последний, но очень важный вопрос!\n\nПоделитесь, пожалуйста, подробными впечатлениями о посещении нашего магазина:\n\n🔹 Что вам больше всего понравилось?\n🔹 Какую посуду вы приобрели?\n🔹 Устроило ли вас качество товаров?\n🔹 Что мы могли бы улучшить?\n🔹 Порекомендуете ли нас друзьям?\n\nВаши отзывы помогают нам становиться лучше! 💪',
        'thank_you':
        '🙏 {name}, огромное спасибо за ваш подробный и честный отзыв о нашем магазине посуды!\n\n🍽️ Мы обязательно:\n• Учтем все ваши замечания\n• Поделимся похвалой с консультантом {consultant}\n• Будем работать над улучшением сервиса\n\n✨ Приходите к нам снова! У нас регулярно появляются новинки кухонной посуды и проводятся акции для постоянных клиентов!\n\n🎁 Следите за нашими обновлениями!'
    },
    'kz': {
        'ask_name':
        '🍽️ "Iposuda" ыдыс дүкеніне қош келдіңіз!\n\n👋 Біз әр сатып алушыны бағалаймыз және қызметіміздің сапасын жақсартқымыз келеді. Сіздің пікіріңіз біз үшін өте маңызды!\n\nТанысайық! Сіздің атыңыз қандай?',
        'consultant':
        '👨‍💼 Керемет, {name}! Ас үй ыдысын сатып алу үшін біздің дүкенді таңдағаныңыз үшін рахмет.\n\nАйтыңызшы, қай консультант сізге тауар таңдауда көмектесті? (Атын жазыңыз немесе қызметкерді сипаттаңыз)\n\nБұл бізге ең жақсы мамандарды ескертуге көмектеседі! 🏆',
        'rate':
        '⭐ {name}, консультант {consultant} жұмысын шынайы бағалағаныңыз үшін өте ризамын.\n\nОл сізге:\n• Тиісті ыдысты табуға көмектесті ме?\n• Тауар сипаттамалары туралы айтты ма?\n• Сыпайы және кәсіби болды ма?\n\nОның жұмысын 1-ден 10-ға дейін бағалаңыз:\n1-3 = қанағаттанарлықсыз 😞\n4-6 = қанағаттанарлық 😐\n7-8 = жақсы 😊\n9-10 = керемет! 🌟',
        'city':
        '🏙️ Өте жақсы! Қай қаладансыз? Бұл бізге сатып алушыларымыздың географиясын түсінуге және мүмкін сіздің аймағыңызда жаңа сату орындарын ашуға көмектеседі! 📍',
        'comment':
        '💭 Ал соңғы, бірақ өте маңызды сұрақ!\n\nБіздің дүкенге келгеніңіз туралы толық әсеріңізбен бөлісіңіз:\n\n🔹 Сізге не ең көп ұнады?\n🔹 Қандай ыдыс сатып алдыңыз?\n🔹 Тауар сапасы ұнады ма?\n🔹 Не жақсартуға болады?\n🔹 Достарыңызға ұсынар ма едіңіз?\n\nСіздің пікірлеріңіз бізге жақсаруға көмектеседі! 💪',
        'thank_you':
        '🙏 {name}, біздің ыдыс дүкені туралы толық және шынайы пікіріңіз үшін зор рахмет!\n\n🍽️ Біз міндетті түрде:\n• Барлық ескертулеріңізді ескереміз\n• Консультант {consultant} мақтауымызбен бөлісеміз\n• Қызметті жақсарту бойынша жұмыс істейміз\n\n✨ Бізге қайта келіңіз! Бізде тұрақты түрде ас үй ыдысының жаңалықтары пайда болады және тұрақты клиенттер үшін акциялар өткізіледі!\n\n🎁 Біздің жаңартуларымызды қадағалаңыз!'
    },
    'uz': {
        'ask_name':
        '🍽️ "Iposuda" idish do\'koniga xush kelibsiz!\n\n👋 Biz har bir xaridorni qadrlaymiz va xizmat sifatimizni yaxshilamoqchimiz. Sizning fikringiz biz uchun juda muhim!\n\nKeling tanishaylik! Ismingiz nima?',
        'consultant':
        '👨‍💼 Ajoyib, {name}! Oshxona idishlarini sotib olish uchun bizning do\'konni tanlaganingiz uchun rahmat.\n\nAyting-chi, qaysi konsultant sizga tovar tanlashda yordam berdi? (Ismini yozing yoki xodimni tasvirlab bering)\n\nBu bizga eng yaxshi mutaxassislarni e\'tirof etishga yordam beradi! 🏆',
        'rate':
        '⭐ {name}, konsultant {consultant} ishini samimiy baholaganingiz uchun juda minnatdormiz.\n\nU sizga:\n• Mos idish topishda yordam berdimi?\n• Tovar xususiyatlari haqida gapirib berdimi?\n• Muloyim va professional edimi?\n\nUning ishini 1 dan 10 gacha baholang:\n1-3 = qoniqarsiz 😞\n4-6 = qoniqarli 😐\n7-8 = yaxshi 😊\n9-10 = ajoyib! 🌟',
        'city':
        '🏙️ Zo\'r! Qaysi shahardansiz? Bu bizga xaridorlarimizning geografiyasini tushunishga va ehtimol sizning hududingizda yangi sotuv nuqtalarini ochishga yordam beradi! 📍',
        'comment':
        '💭 Va oxirgi, lekin juda muhim savol!\n\nBizning do\'konga tashrif buyurganingiz haqida batafsil taassurotlaringiz bilan bo\'lishing:\n\n🔹 Sizga eng ko\'p nima yoqdi?\n🔹 Qanday idish sotib oldingiz?\n🔹 Tovar sifati yoqdimi?\n🔹 Nimani yaxshilash mumkin?\n🔹 Do\'stlaringizga tavsiya qilasizmi?\n\nSizning fikrlaringiz bizga yaxshilanishga yordam beradi! 💪',
        'thank_you':
        '🙏 {name}, bizning idish do\'konimiz haqida batafsil va samimiy fikringiz uchun katta rahmat!\n\n🍽️ Biz albatta:\n• Barcha izohlaringizni hisobga olamiz\n• Konsultant {consultant} bilan maqtovimizni bo\'lishamiz\n• Xizmatni yaxshilash bo\'yicha ishlash davom etamiz\n\n✨ Bizga yana tashrif buyuring! Bizda muntazam ravishda oshxona idishlarining yangiliklari paydo bo\'ladi va doimiy mijozlar uchun aksiyalar o\'tkaziladi!\n\n🎁 Bizning yangilanishlarimizni kuzatib boring!'
    },
}

lang_buttons = ReplyKeyboardMarkup(keyboard=[[
    KeyboardButton(text="🇷🇺 Русский"),
    KeyboardButton(text="🇰🇿 Қазақша"),
    KeyboardButton(text="🇺🇿 O‘zbekcha")
]],
                                   resize_keyboard=True)

rating_buttons = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=str(i)) for i in range(1, 6)],
              [KeyboardButton(text=str(i)) for i in range(6, 11)]],
    resize_keyboard=True)


# === /start ===
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    welcome_text = (
        "🍽️ Добро пожаловать в систему отзывов магазина посуды 'Iposuda'!\n\n"
        "✨ Мы стремимся предоставить вам лучшую посуду и сервис высочайшего качества.\n\n"
        "📝 Ваш отзыв поможет нам:\n"
        "• Улучшить качество обслуживания\n"
        "• Подобрать лучший ассортимент\n"
        "• Обучить наших консультантов\n"
        "• Сделать покупки еще удобнее\n\n"
        "🌍 Пожалуйста, выберите ваш язык:")
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
    await message.answer(languages[lang]['ask_name'],
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(Feedback.name)


@dp.message(Feedback.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
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
    await message.answer(languages[data['lang']]['city'],
                         reply_markup=ReplyKeyboardRemove())
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

    # Сообщение админу
    summary = (f"📋 Новый отзыв:\n"
               f"👤 Имя: {data['name']}\n"
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
                data['name'], data['consultant'], data['rating'], data['city'],
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
