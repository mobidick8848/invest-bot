import os
import asyncio
import sqlite3
import csv
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.utils.token import validate_token, TokenValidationError
from aiogram.client.default import DefaultBotProperties

# --- Получаем токен и канал ---
TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not TOKEN:
    raise RuntimeError("Env BOT_TOKEN is empty. Set it in Railway → Variables.")
try:
    validate_token(TOKEN)
except TokenValidationError:
    raise RuntimeError("BOT_TOKEN has invalid format.")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# --- Настройка БД ---
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            profile TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_result(user_id, username, profile):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO results (user_id, username, profile, date) VALUES (?, ?, ?, ?)",
                (user_id, username, profile, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT profile, COUNT(*) FROM results GROUP BY profile")
    rows = cur.fetchall()
    conn.close()
    return rows

# --- Клавиатура ---
def kb(options):
    builder = InlineKeyboardBuilder()
    for text, val in options:
        builder.button(text=text, callback_data=f"v|{val}")
    builder.adjust(1)
    return builder.as_markup()

# --- Машина состояний ---
class Quiz(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()

# --- Начало ---
@dp.message(CommandStart())
async def start_handler(m: types.Message, state: FSMContext):
    await m.answer("Привет 👋 Я помогу определить твой риск-профиль.\n\nПервый вопрос:")
    await m.answer("📊 Какой у тебя инвестиционный горизонт?",
        reply_markup=kb([("<1 года","0"),("1–3 года","1"),("3–5 лет","2"),(">5 лет","3")]))
    await state.set_state(Quiz.q1)

# --- Вопросы ---
@dp.callback_query(Quiz.q1)
async def q1_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    await state.update_data(score=int(val))
    await c.message.edit_text("🧠 Какую просадку ты готов(а) выдержать?",
        reply_markup=kb([("2%","0"),("5%","1"),("10%","2"),("20%+","3")]))
    await state.set_state(Quiz.q2)

@dp.callback_query(Quiz.q2)
async def q2_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    data = await state.get_data()
    score = data["score"] + int(val)
    await state.update_data(score=score)
    await c.message.edit_text("💰 Какой у тебя ежемесячный бюджет для инвестиций?",
        reply_markup=kb([("<10 000 ₽","0"),("10 000–50 000 ₽","1"),("50 000–200 000 ₽","2"),(">200 000 ₽","3")]))
    await state.set_state(Quiz.q3)

@dp.callback_query(Quiz.q3)
async def q3_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    data = await state.get_data()
    score = data["score"] + int(val)
    await state.update_data(score=score)
    await c.message.edit_text("🧾 Какой у тебя опыт инвестиций?",
        reply_markup=kb([("Нет опыта","0"),("1–3 года","1"),("3–5 лет","2"),("Более 5 лет","3")]))
    await state.set_state(Quiz.q4)

@dp.callback_query(Quiz.q4)
async def q4_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    data = await state.get_data()
    score = data["score"] + int(val)
    await state.update_data(score=score)
    await c.message.edit_text("🎯 Какова цель твоих инвестиций?",
        reply_markup=kb([("Сохранить деньги","0"),("Пассивный доход","1"),("Умеренный рост","2"),("Максимальный рост","3")]))
    await state.set_state(Quiz.q5)

# --- Вопрос 5 (результат) ---
@dp.callback_query(Quiz.q5)
async def q5_handler(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split("|")
    data = await state.get_data()
    score = data["score"] + int(val)

    if score <= 4:
        profile = "C"
        advice = "Облигации, депозиты, минимальный риск."
    elif score <= 7:
        profile = "M"
        advice = "Часть облигаций + фонды акций."
    elif score <= 10:
        profile = "B"
        advice = "Пропорция акций и облигаций, можно ETF."
    elif score <= 13:
        profile = "G"
        advice = "Акции, ETF на индексы, немного альтернатив."
    else:
        profile = "A"
        advice = "Акции роста, криптовалюты, венчур."

    profiles_table = (
        "📊 <b>Инвестиционные профили</b>\n\n"
        "C — Консервативный: сохранение капитала, облигации, депозиты\n"
        "M — Умеренный: умеренный рост, облигации + акции\n"
        "B — Сбалансированный: баланс доходности и риска, акции + облигации\n"
        "G — Ростовой: рост капитала, акции, фонды\n"
        "A — Агрессивный: максимальный риск, акции роста, криптовалюты\n"
    )

    save_result(c.from_user.id, c.from_user.username, profile)

    await c.message.edit_text(
        f"✅ Спасибо за ответы!\n\n"
        f"Твой профиль: <b>{profile}</b>\n"
        f"💡 Рекомендация: {advice}\n\n"
        f"{profiles_table}\n"
        f"⚠️ Это не инвестиционная рекомендация."
    )

    img_path = os.path.join(os.path.dirname(__file__), "assets", "profiles.png")
    if os.path.exists(img_path):
        await c.message.answer_photo(types.FSInputFile(img_path))

    await state.clear()

# --- Команда /stats ---
@dp.message(Command("stats"))
async def stats_handler(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔ У вас нет доступа к этой команде.")
    rows = get_stats()
    if not rows:
        return await m.answer("📊 Пока нет данных.")
    text = "📊 Статистика:\n"
    for profile, count in rows:
        text += f"{profile} — {count} пользователей\n"
    await m.answer(text)

# --- Команда /export ---
@dp.message(Command("export"))
async def export_handler(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔ У вас нет доступа к этой команде.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, profile, date FROM results")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await m.answer("📂 Нет данных для экспорта.")

    file_path = os.path.join(os.path.dirname(__file__), "export.csv")
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "username", "profile", "date"])
        writer.writerows(rows)

    await m.answer_document(types.FSInputFile(file_path))

# --- Автопостинг ---
async def send_channel_post():
    if CHANNEL_ID != 0:
        text = (
            "🔥 Какой ты инвестор?\n"
            "C — Консервативный 🛡\n"
            "M — Умеренный ⚖\n"
            "B — Сбалансированный ⚡\n"
            "G — Ростовой 🚀\n"
            "A — Агрессивный 💎\n\n"
            "Пройди тест и узнай свой профиль 👇"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="🚀 Запустить тест", url="https://t.me/FinInvestAI_bot?start=start")
        await bot.send_message(CHANNEL_ID, text, reply_markup=kb.as_markup())

async def scheduler():
    while True:
        await send_channel_post()
        await asyncio.sleep(3 * 24 * 60 * 60)

# --- Запуск ---
async def main():
    init_db()
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
