from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
import aiosqlite
import random
import string
from config import DB_PATH, USERNAME_PRICE

router = Router()

# Yangi qo'shilgan tugmalar
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Qisqa noyob so'z username")],
        [KeyboardButton(text="Turli ko'rinishdagi username")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Tanlang..."
)

from bot.words import generate_smart_username

def generate_short_username():
    length = random.randint(3, 5)
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

@router.message(CommandStart())
async def start_cmd(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (telegram_id, balance) VALUES (?, ?)", (message.from_user.id, USERNAME_PRICE))
        await db.commit()
    # O'zgartirilgan joyi: reply_markup=keyboard qo'shildi
    await message.answer(
        "Xush kelibsiz! Bu bot orqali avtomatik qisqa va ma'noli usernamelarni sotib olishingiz mumkin.\n\nYoki quyidagi tugmalar yordamida yangi usernamelar yaratishingiz mumkin:", 
        reply_markup=keyboard
    )

@router.message(F.text == "Qisqa noyob so'z username")
async def short_username_handler(message: Message):
    usernames = [f"@{generate_short_username()}" for _ in range(5)]
    response = "Mana sizga qisqa noyob usernamelar:\n\n" + "\n".join(usernames)
    await message.answer(response)

@router.message(F.text == "Turli ko'rinishdagi username")
async def various_username_handler(message: Message):
    usernames = [f"@{generate_smart_username()}" for _ in range(5)]
    response = "Mana sizga turli ko'rinishdagi usernamelar:\n\n" + "\n".join(usernames)
    await message.answer(response)
