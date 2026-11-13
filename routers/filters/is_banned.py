from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from ..commands.admin import ban_list


class IsBanned(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery):
        return event.from_user is not None and event.from_user.id in ban_list
