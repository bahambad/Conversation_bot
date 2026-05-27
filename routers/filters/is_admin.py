
from aiogram.types import Message
from aiogram.filters import Command,  BaseFilter
from typing import List


class IsAdmin(BaseFilter):

    def __init__(self, admin_id: int | List[int]) -> None:
        self.admin_id = admin_id

    async def __call__(self, message: Message):
        if isinstance(self.admin_id, int):
            return message.from_user.id == self.admin_id
        return message.from_user.id in self.admin_id
