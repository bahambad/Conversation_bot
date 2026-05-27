from aiogram import Router, types
from aiogram.filters import BaseFilter
from aiogram.types import Message

from .commands.admin import ban_list
from .filters.is_banned import IsBanned

Router = Router(name=__name__)

@Router.message(IsBanned())
async def banned_user_handler(message: types.Message):
    return