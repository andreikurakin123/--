from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command



router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[

            [KeyboardButton(text="➕ Добавить пациента"), KeyboardButton(text="➕ Добавить врача")],
            [KeyboardButton(text="📝 Назначить лечение"), KeyboardButton(text="📋 Заполнить состояние пациента")],
            [KeyboardButton(text="📈 Отчёты"), KeyboardButton(text="📊 Показать таблицу"), KeyboardButton(text="Уволить врача")],
            [KeyboardButton(text="Начать"), KeyboardButton(text="Помощь"), KeyboardButton(text="Вторая часть: отчет")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🏥 Добро пожаловать в систему управления больницей!\n\nВыберите действие:",
        reply_markup=keyboard
    )

@router.message(F.text == "➕ Добавить пациента")
async def add_patient_menu(message: Message):
    await message.answer("Чтобы добавить пациента, введите команду /add_patient")

@router.message(F.text == "➕ Добавить врача")
async def add_doctor_menu(message: Message):
    await message.answer("Чтобы добавить врача, введите команду /add_doctor")

@router.message(F.text == "Уволить врача")
async def dismiss_doctor_menu(message: Message):  # и лучше поменять имя функции
    await message.answer("Чтобы уволить врача, введите команду /dismiss_doctor")

@router.message(F.text == "📝 Назначить лечение")
async def assign_treatment_menu(message: Message):
    await message.answer("Чтобы назначить лечение пациенту, введите команду /assign_treatment")

@router.message(F.text == "📋 Заполнить состояние пациента")
async def update_status_menu(message: Message):
    await message.answer("Чтобы обновить состояние пациента, введите команду /update_status")

@router.message(F.text == "📊 Показать таблицу")
async def print_table(message: Message):
    await message.answer("Чтобы увидеть таблицы, введите команду /show_table")

@router.message(F.text == "Помощь")
async def help(message: Message):
    await message.answer("Чтобы увидеть список команд, введите команду /help")


@router.message(F.text == "Начать")
async def start(message: Message):
    await message.answer("Чтобы начать работу бота, введите команду /start")
    
@router.message(F.text == "Вторая часть: отчет")
async def tests(message: Message):
    await message.answer("Чтобы посмотреть отчет ко второй части, введите команду /standard_operations")
    
@router.message(F.text == "📈 Отчёты")
async def reports_menu(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/report_dead_patients")],
            [KeyboardButton(text="/report_best_doctors")],
            [KeyboardButton(text="/report_disease_frequency")],
            [KeyboardButton(text="/report_hospital_history")],
            [KeyboardButton(text="🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите тип отчета:", reply_markup=keyboard)

@router.message(F.text == "🔙 Назад в главное меню")
async def back_to_main_menu(message: Message):
    await cmd_start(message)



