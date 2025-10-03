import os, asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.utils.token import validate_token, TokenValidationError

TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
if not TOKEN:
    raise RuntimeError("Env BOT_TOKEN is empty. Set it in Railway → Variables.")
try:
    validate_token(TOKEN)
except TokenValidationError:
    raise RuntimeError("BOT_TOKEN has invalid format. Must look like '123456789:AA...'.")
print(f"BOT_TOKEN ok (masked tail: …{TOKEN[-6:]})")

class Quiz(StatesGroup):
    q1 = State()
    q2 = State()
    done = State()
    
bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

def kb(options):
    builder = InlineKeyboardBuilder()
    for text, val in options:
        builder.button(text=text, callback_data=f"v|{val}")
    builder.adjust(2)
    return builder.as_markup()

@dp.message(CommandStart())
async def start_handler(m: types.Message, state: FSMContext):
    await m.answer("Привет 👋 Я помогу определить твой риск-профиль.\n\nПервый вопрос:")
    await m.answer("📊 Какой у тебя инвестиционный горизонт?",
        reply_markup=kb([("<1 года","0"),("1–3 года","1"),("3–5 лет","2"),(">5 лет","3")]))
    await state.set_state(Quiz.q1)

@dp.callback_query(Quiz.q1)
async def q1_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    await state.update_data(horizon=int(val))
    await c.message.edit_text("🧠 Какую просадку ты готов(а) выдержать?",
        reply_markup=kb([("2%","0"),("5%","1"),("10%","2"),("20%+","3")]))
    await state.set_state(Quiz.q2)

@dp.callback_query(Quiz.q2)
async def q2_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    data = await state.get_data()
    horizon = data.get("horizon", 0)
    risk = int(val)
    score = horizon + risk
    if score <= 2:
        profile = "C (консервативный)"
    elif score <= 3:
        profile = "M (умеренный)"
    else:
        profile = "B/G (ростовой)"
    await c.message.edit_text(
        f"✅ Спасибо за ответы!\n\nТвой базовый профиль: <b>{profile}</b>.\n"
        "⚠️ Это не инвестиционная рекомендация."
    )
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
