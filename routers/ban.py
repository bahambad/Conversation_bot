from aiogram import Router, types

from .filters.is_banned import IsBanned

Router = Router(name=__name__)

@Router.message(IsBanned())
async def banned_user_handler(message: types.Message):
    await message.answer("Этот бот только для людей, у которых есть совесть")
    return