import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message, TelegramObject

TOO_FAST_TEXT = "😮‍💨 Too fast!"


@dataclass
class _UserState:
    last_passed: float = 0.0  # время последнего пропущенного события
    count: int = 0  # событий подряд в пределах time_limit
    warnings: int = 0
    first_warning: float = 0.0
    muted_until: float = 0.0


class ThrottlingMiddleware(BaseMiddleware):
    """
    Антифлуд для сообщений и нажатий на inline-кнопки (счётчик общий).

    Больше message_limit событий с интервалом меньше time_limit — предупреждение,
    warnings_limit предупреждений за warnings_time_limit секунд — игнор на mute_time секунд.
    """

    def __init__(
            self,
            message_limit: int = 2,
            time_limit: float = 1.7,
            warnings_limit: int = 3,
            warnings_time_limit: float = 10,
            mute_time: float = 10,
            cleanup_interval: float = 60,
    ) -> None:
        self.message_limit = message_limit
        self.time_limit = time_limit
        self.warnings_limit = warnings_limit
        self.warnings_time_limit = warnings_time_limit
        self.mute_time = mute_time
        self.cleanup_interval = cleanup_interval
        self._users: Dict[int, _UserState] = {}
        self._last_cleanup = time.monotonic()
        self._background_tasks: set[asyncio.Task] = set()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        self._cleanup(now)
        state = self._users.setdefault(user.id, _UserState())

        if now < state.muted_until:
            return None

        if state.last_passed and now - state.last_passed <= self.time_limit:
            state.count += 1
            if state.count > self.message_limit:
                state.warnings += 1
                if state.warnings == 1:
                    state.first_warning = now
                    await self._warn(event)
                elif (state.warnings >= self.warnings_limit
                      and now - state.first_warning <= self.warnings_time_limit):
                    state.muted_until = now + self.mute_time
                    state.warnings = 0
                return None
        else:
            state.count = 1
            state.warnings = 0

        state.last_passed = now
        return await handler(event, data)

    def _cleanup(self, now: float) -> None:
        """Удаляет записи давно не писавших пользователей, чтобы словарь не рос бесконечно."""
        if now - self._last_cleanup < self.cleanup_interval:
            return
        self._last_cleanup = now
        ttl = max(self.time_limit, self.warnings_time_limit, self.mute_time)
        stale = [
            user_id for user_id, state in self._users.items()
            if now - state.last_passed > ttl and now >= state.muted_until
        ]
        for user_id in stale:
            del self._users[user_id]

    async def _warn(self, event: TelegramObject) -> None:
        with suppress(TelegramAPIError):
            if isinstance(event, CallbackQuery):
                await event.answer(TOO_FAST_TEXT)
            elif isinstance(event, Message):
                warning = await event.answer(text=f"<b>{TOO_FAST_TEXT}</b>",
                                             parse_mode=ParseMode.HTML)
                # Удаляем предупреждение в фоне, не задерживая обработку
                task = asyncio.create_task(self._delete_later(warning))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    @staticmethod
    async def _delete_later(message: Message, delay: float = 2) -> None:
        await asyncio.sleep(delay)
        with suppress(TelegramAPIError):
            await message.delete()
