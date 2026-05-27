from aiogram.filters import BaseFilter
from aiogram.types import Message

from ..commands.admin import ban_list

class IsBanned(BaseFilter):
    async def __call__(self, message: Message):
        return message.from_user.id in ban_list