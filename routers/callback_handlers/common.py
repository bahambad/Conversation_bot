from contextlib import suppress
from pathlib import Path
from typing import Optional, TypeVar

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery

from modules.errors import ProcessingError
from modules.jobs import is_busy
from modules.storage import TTLStore
from modules.thumbnails import make_audio_cover
from modules.yt_downloads import DownloadedMedia

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


async def send_downloaded_audio(bot: Bot, chat_id: int, media: DownloadedMedia, workdir: Path) -> None:
    """Отправляет скачанное аудио с названием, каналом в поле исполнителя и обложкой."""
    cover = None
    if media.thumbnail is not None:
        # Обложка — приятное дополнение: без неё аудио всё равно отправляем
        cover_path = workdir / "cover.jpg"
        with suppress(ProcessingError):
            await make_audio_cover(media.thumbnail, cover_path)
            cover = FSInputFile(path=cover_path)
    await bot.send_audio(chat_id, audio=FSInputFile(path=media.path, filename=media.filename),
                         title=media.title, performer=media.performer, thumbnail=cover)
