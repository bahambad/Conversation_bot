from contextlib import suppress
from typing import Optional, TypeVar

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery

from modules.jobs import is_busy
from modules.storage import TTLStore

EXPIRED_TEXT = "⌛️ This button has expired. Please send it again."
NOT_YOURS_TEXT = "This button is for the person who sent the request."
BUSY_ALERT_TEXT = "⏳ Your previous request is still being processed. Please wait."

T = TypeVar("T")


async def claim_entry(call: CallbackQuery, bot: Bot, store: TTLStore[T], key: str) -> Optional[T]:
    """
    Забирает из хранилища запрос, привязанный к inline-кнопке.

    Возвращает None (и сам отвечает на callback), если кнопка устарела,
    нажата не автором запроса или у пользователя уже выполняется тяжёлая задача.
    У записи в хранилище должно быть поле user_id.
    """
    entry = store.get(key)
    if entry is None:
        await call.answer(EXPIRED_TEXT, show_alert=True)
        with suppress(TelegramAPIError):
            await bot.delete_message(call.message.chat.id, call.message.message_id)
        return None
    if entry.user_id != call.from_user.id:
        await call.answer(NOT_YOURS_TEXT, show_alert=True)
        return None
    if is_busy(call.from_user.id):
        # Кнопку не трогаем: ей можно будет воспользоваться, когда закончится предыдущая задача
        await call.answer(BUSY_ALERT_TEXT, show_alert=True)
        return None
    store.pop(key)
    return entry
