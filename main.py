import asyncio
import logging

from decouple import config
from aiogram import Dispatcher, Bot

from middlewares.antiflood import ThrottlingMiddleware

from routers import router as main_router


dp = Dispatcher()
dp.include_router(main_router)

# Один экземпляр на сообщения и на кнопки: тяжёлые операции запускаются именно кнопками
throttling = ThrottlingMiddleware()
dp.message.outer_middleware(throttling)
dp.callback_query.outer_middleware(throttling)


async def main():
    logging.basicConfig(level=logging.INFO)
    bot_token = config('BOT_TOKEN')
    bot = Bot(token=bot_token)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
