import asyncio
import logging

from aiogram.utils.keyboard import ReplyKeyboardBuilder
from decouple import config
from aiogram import Dispatcher, Bot
# from config import bot

from routers import router as main_router


dp = Dispatcher()
dp.include_router(main_router)


async def main():
    logging.basicConfig(level=logging.INFO)
    bot_token = config('BOT_TOKEN')
    bot = Bot(token=bot_token)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
