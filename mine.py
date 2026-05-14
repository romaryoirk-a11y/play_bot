import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

DB_PATH = "casino.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

def roll_dice(bet: int):
    roll = random.randint(1, 6)
    won = roll > 3
    payout = bet * 2 if won else 0
    return roll, won, payout

dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🎰 Добро пожаловать в демо-казино!\n\n"
        "📜 Команды:\n"
        "/dice <сумма> — сыграть в кости (выпадет 4-6 = победа x2)\n"
        "/balance — проверить баланс\n"
        "/addcoins <сумма> — пополнить виртуальные монеты (только для тестов)"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    bal = await get_balance(message.from_user.id)
    await message.answer(f"💰 Ваш баланс: {bal} монет")

@dp.message(Command("addcoins"))
async def cmd_add(message: Message, args: str = ""):
    try:
        amount = int(args)
        if amount <= 0:
            raise ValueError
        await update_balance(message.from_user.id, amount)
        await message.answer(f"✅ Начислено {amount} монет. Баланс: {await get_balance(message.from_user.id)}")
    except (ValueError, TypeError):
        await message.answer("❌ Формат: `/addcoins 100`", parse_mode="Markdown")

@dp.message(Command("dice"))
async def cmd_dice(message: Message, args: str = ""):
    try:
        bet = int(args)
        if bet <= 0:
            raise ValueError
        bal = await get_balance(message.from_user.id)
        if bet > bal:
            return await message.answer("❌ Недостаточно монет!")

        await update_balance(message.from_user.id, -bet)
        roll, won, payout = roll_dice(bet)
        await update_balance(message.from_user.id, payout)

        new_bal = bal - bet + payout
        emoji = "🎉" if won else "😔"
        text = (
            f"{emoji} Бросок: {roll}\n"
            f"{'Вы выиграли!' if won else 'Вы проиграли.'}\n"
            f"💰 Баланс: {new_bal} монет"
        )
        await message.answer(text)
    except (ValueError, TypeError):
        await message.answer("❌ Формат: `/dice 50`", parse_mode="Markdown")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
