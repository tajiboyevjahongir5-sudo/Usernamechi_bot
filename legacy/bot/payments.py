from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import PAYMENT_CARD, ADMIN_CHANNEL
import aiosqlite
from config import DB_PATH

router = Router()

@router.message(F.photo)
async def handle_payment_receipt(message: Message):
    # Agar foydalanuvchi rasm tashlasa (chek), adminga yuboramiz
    caption = f"💰 Yangi to'lov cheki!\nFoydalanuvchi: {message.from_user.id}\nSummani tasdiqlang:"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ 50,000 so'm", callback_data=f"approve_{message.from_user.id}_50000")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{message.from_user.id}")]
    ])
    
    await message.bot.send_photo(
        chat_id=ADMIN_CHANNEL, 
        photo=message.photo[-1].file_id, 
        caption=caption, 
        reply_markup=markup
    )
    await message.answer("✅ Chek adminga yuborildi. Tasdiqlangach, balansingizga pul tushadi.")

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(call: CallbackQuery):
    _, user_id, amount = call.data.split("_")
    user_id = int(user_id)
    amount = int(amount)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, user_id))
        await db.commit()
        
    await call.message.edit_caption(caption=f"✅ To'lov tasdiqlandi. ({amount} so'm tushirildi).")
    await call.bot.send_message(chat_id=user_id, text=f"🎉 Balansingiz {amount} so'mga to'ldirildi!")
