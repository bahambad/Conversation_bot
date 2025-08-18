import asyncio
import time

from aiogram import BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.types import Message

from collections import Counter
from typing import Callable, Awaitable, Dict, Any


class MessageThrottlingMiddleware(BaseMiddleware):

    def __init__(
            self,
            message_limit: int = 2,
            time_limit: float = 1.7,
            warnings_limit: int = 3,
            warnings_time_limit: int = 10
    ) -> None:
        self.message_limit = message_limit
        self.time_limit = time_limit
        self.warnings_limit = warnings_limit
        self.warnings_time_limit = warnings_time_limit
        self.message_counter = Counter()
        self.warning_counter = Counter()
        self.warning_time = {}
        self.first_warning_time = {}
        self.ban_status = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()

        if user_id in self.ban_status:
            if self.ban_status[user_id] is True:
                return
        if user_id in self.warning_time:
            time_since_last_message = current_time - self.warning_time[user_id]
            if time_since_last_message <= self.time_limit:
                self.message_counter[user_id] += 1
                if self.message_counter[user_id] > self.message_limit:
                    self.warning_counter[user_id] += 1
                    if self.warning_counter[user_id] == 1:
                        self.first_warning_time[user_id] = current_time
                        antiflood_msg = await Message.answer(text='<b>😮‍💨 Too fast!</b>',
                                                             parse_mode=ParseMode.HTML,
                                                             self=event)
                        await asyncio.sleep(2)
                        await antiflood_msg.delete()
                        return
                    else:
                        if self.warning_counter[user_id] > 2:
                            if current_time - self.first_warning_time[user_id] <= self.warnings_time_limit:
                                self.ban_status[user_id] = True
                                # Блокировка пользователя на 10 секунд
                                await asyncio.sleep(10)
                                self.ban_status[user_id] = False
                                self.warning_counter[user_id] = 0
                                return
                    return
            else:
                self.warning_counter[user_id] = 0
                self.message_counter[user_id] = 1
        else:
            self.warning_counter[user_id] = 0
            self.message_counter[user_id] = 1

        self.warning_time[user_id] = current_time
        return await handler(event, data)