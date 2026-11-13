import asyncio
from contextlib import suppress

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from keyboards.yt_dlp_keyboard import UrlOfVideoCdData
from modules.jobs import heavy_job, job_dir, report_errors
from modules.yt_downloads import download_media
from routers.callback_handlers.common import claim_entry, send_downloaded_audio
from routers.video_processing import url_storage

router = Router(name=__name__)


# Один обработчик на скачивание и видео, и аудио по ссылке
@router.callback_query(UrlOfVideoCdData.filter(F.operation.in_({"audio", "video"})))
async def process_url(call: CallbackQuery, callback_data: UrlOfVideoCdData, bot: Bot):
    audio_only = callback_data.operation == "audio"
    chat_id = call.message.chat.id
    keyboard_message_id = call.message.message_id

    entry = await claim_entry(call, bot, url_storage, callback_data.url_id)
    if entry is None:
        return

    async with report_errors(bot, chat_id):
        async with heavy_job(call.from_user.id):
            await call.answer()
            with suppress(TelegramAPIError):
                await bot.delete_message(chat_id, keyboard_message_id)

            if audio_only:
                text = "Okay, i got it. Now i'm going to download audio from this video"
                action = ChatAction.UPLOAD_DOCUMENT
            else:
                text = "Okay, i got it. Now i'm going to download this video"
                action = ChatAction.UPLOAD_VIDEO
            waiting_message = await bot.send_message(chat_id, text)
            try:
                with job_dir() as workdir:
                    async with ChatActionSender(bot=bot, chat_id=chat_id, action=action):
                        # yt-dlp блокирующий, поэтому выполняем его в отдельном потоке
                        media = await asyncio.to_thread(download_media, entry.url, workdir, audio_only)

                        if audio_only:
                            await send_downloaded_audio(bot, chat_id, media, workdir)
                        else:
                            file = types.FSInputFile(path=media.path, filename=media.filename)
                            await bot.send_video(chat_id, video=file)
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()
