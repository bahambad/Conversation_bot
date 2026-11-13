"""
Экспериментальная функция: скачивание фрагмента видео по таймкодам.

Доступна только админу и нигде в сообщениях бота не упоминается.
Скачивается только указанный отрезок, поэтому исходное видео может быть любого размера.
"""
import asyncio
from contextlib import suppress

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from keyboards.yt_dlp_keyboard import UrlOfVideoCdData
from modules.jobs import heavy_job, job_dir, report_errors
from modules.permissions import is_admin
from modules.timecodes import format_timecode, parse_time_range
from modules.yt_downloads import (MAX_AUDIO_FRAGMENT_DURATION, MAX_FRAGMENT_DURATION, MAX_FRAGMENT_SIZE,
                                  download_media)
from routers.callback_handlers.common import claim_entry, send_downloaded_audio
from routers.video_processing import url_storage
from states import Fragment

router = Router(name=__name__)

# Время на скачивание и перекодирование фрагмента, секунд
FRAGMENT_TIMEOUT = 900

ASK_TEXT = """✂️ Send the timecodes of the {kind} fragment: <code>start-end</code>

For example <code>1:02:30-1:03:10</code> or <code>90-150</code> (seconds).
The fragment can be up to {max_length} long.

Send /cancel to stop."""
INVALID_TEXT = """⛔️ I can't read these timecodes.
Send them as <code>start-end</code>, for example <code>1:02:30-1:03:10</code>, or /cancel."""
TOO_LONG_TEXT = "⛔️ The fragment can be up to {max_length} long."


def _max_duration(audio_only: bool) -> int:
    # Аудио намного легче видео и не требует перекодирования картинки, поэтому отрезок может быть длиннее
    return MAX_AUDIO_FRAGMENT_DURATION if audio_only else MAX_FRAGMENT_DURATION


@router.callback_query(UrlOfVideoCdData.filter(F.operation.in_({"fragment", "fragment_audio"})))
async def ask_timecodes(call: CallbackQuery, callback_data: UrlOfVideoCdData, bot: Bot, state: FSMContext):
    # Кнопку видит только админ, но callback_data можно подделать
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    entry = await claim_entry(call, bot, url_storage, callback_data.url_id)
    if entry is None:
        return

    await call.answer()
    with suppress(TelegramAPIError):
        await bot.delete_message(call.message.chat.id, call.message.message_id)

    audio_only = callback_data.operation == "fragment_audio"
    await state.set_state(Fragment.timecodes)
    await state.update_data(fragment_url=entry.url, fragment_audio=audio_only)
    text = ASK_TEXT.format(kind="audio" if audio_only else "video",
                           max_length=format_timecode(_max_duration(audio_only)))
    await bot.send_message(call.message.chat.id, text, parse_mode=ParseMode.HTML)


@router.message(Fragment.timecodes, F.text)
async def download_fragment(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    chat_id = message.chat.id
    data = await state.get_data()
    url = data.get("fragment_url")
    audio_only = bool(data.get("fragment_audio"))
    if not is_admin(user_id) or not url:
        await state.clear()
        return

    try:
        start, end = parse_time_range(message.text)
    except ValueError:
        await message.answer(text=INVALID_TEXT, parse_mode=ParseMode.HTML)
        return
    if end - start > _max_duration(audio_only):
        text = TOO_LONG_TEXT.format(max_length=format_timecode(_max_duration(audio_only)))
        await message.answer(text=text, parse_mode=ParseMode.HTML)
        return

    async with report_errors(bot, chat_id):
        async with heavy_job(user_id):
            waiting_message = await message.answer(
                text=f"✂️ Downloading the fragment {format_timecode(start)}–{format_timecode(end)}..."
            )
            try:
                with job_dir() as workdir:
                    action = ChatAction.UPLOAD_DOCUMENT if audio_only else ChatAction.UPLOAD_VIDEO
                    async with ChatActionSender(bot=bot, chat_id=chat_id, action=action):
                        # yt-dlp блокирующий, поэтому выполняем его в отдельном потоке
                        media = await asyncio.to_thread(
                            download_media, url, workdir, audio_only,
                            max_size=MAX_FRAGMENT_SIZE, timeout=FRAGMENT_TIMEOUT, time_range=(start, end),
                        )
                        if audio_only:
                            await send_downloaded_audio(bot, chat_id, media, workdir)
                        else:
                            file = types.FSInputFile(path=media.path, filename=media.filename)
                            await bot.send_video(chat_id, video=file)
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()

            # Состояние сбрасываем только после успеха: при ошибке можно прислать другие таймкоды
            await state.clear()
