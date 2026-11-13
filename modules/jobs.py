import asyncio
import logging
import shutil
import tempfile
from contextlib import asynccontextmanager, contextmanager, suppress
from pathlib import Path
from typing import AsyncIterator, Iterator

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from modules.errors import FileTooBigError, UserBusyError, UserFacingError
from modules.paths import DOWNLOADS_DIR

logger = logging.getLogger(__name__)

# Максимальный размер файла, который бот может скачать через Bot API
MAX_FILE_SIZE = 20 * 1024 * 1024
# Сколько тяжёлых задач (ffmpeg, yt-dlp) может выполняться одновременно
MAX_PARALLEL_JOBS = 2

_job_slots = asyncio.Semaphore(MAX_PARALLEL_JOBS)
_busy_users: set[int] = set()


def is_busy(user_id: int) -> bool:
    return user_id in _busy_users


@asynccontextmanager
async def heavy_job(user_id: int) -> AsyncIterator[None]:
    """
    Ограничивает нагрузку: одна тяжёлая задача на пользователя
    и не больше MAX_PARALLEL_JOBS задач на весь бот (остальные ждут в очереди).
    """
    if user_id in _busy_users:
        raise UserBusyError()
    _busy_users.add(user_id)
    try:
        async with _job_slots:
            yield
    finally:
        _busy_users.discard(user_id)


@contextmanager
def job_dir() -> Iterator[Path]:
    """
    Уникальная временная папка на одну задачу.

    Файлы разных пользователей не могут пересечься, а папка удаляется
    при любом исходе — в том числе при ошибке.
    """
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(dir=DOWNLOADS_DIR))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def cleanup_downloads() -> None:
    """Удаляет файлы, оставшиеся от прошлого запуска (например, после аварийной остановки)."""
    if not DOWNLOADS_DIR.is_dir():
        return
    for item in DOWNLOADS_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            with suppress(OSError):
                item.unlink()


async def download_tg_file(bot: Bot, file_id: str, file_size: int | None, destination: Path) -> None:
    """Скачивает файл из Telegram, заранее проверяя ограничение Bot API на размер."""
    if file_size is not None and file_size > MAX_FILE_SIZE:
        raise FileTooBigError()
    try:
        file = await bot.get_file(file_id)
    except TelegramBadRequest as e:
        if "too big" in str(e).lower():
            raise FileTooBigError() from e
        raise
    await bot.download_file(file.file_path, destination=destination)


@asynccontextmanager
async def report_errors(bot: Bot, chat_id: int) -> AsyncIterator[None]:
    """Сообщает пользователю о настоящей причине ошибки, а неожиданные ошибки пишет в лог."""
    try:
        yield
    except UserFacingError as e:
        with suppress(TelegramAPIError):
            await bot.send_message(chat_id, e.text, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("Unexpected error while handling a request")
        with suppress(TelegramAPIError):
            await bot.send_message(chat_id, UserFacingError.text, parse_mode=ParseMode.HTML)
