import asyncio
import logging

from aiogram.utils.keyboard import ReplyKeyboardBuilder
from decouple import config
from aiogram import Dispatcher, Bot
# from config import bot

from routers import router as main_router


dp = Dispatcher()
dp.include_router(main_router)


def builder_video_processing_choose_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="To make a video note")
    builder.button(text="To make a voice message")

    return builder.as_markup(resize_keyboard=True)



async def main():
    logging.basicConfig(level=logging.INFO)
    bot_token = config('BOT_TOKEN')
    bot = Bot(token=bot_token)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
