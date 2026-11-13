from contextlib import suppress

from aiogram import Bot, Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.chat_action import ChatActionSender

from modules.audio_defs import voice_from_media
from modules.jobs import download_tg_file, heavy_job, job_dir, report_errors

router = Router(name=__name__)

WAITING_TEXT = "✅ I got it.\nPlease wait a moment..."


# Функция постоянной конвертации Аудио в ГС
@router.message(F.audio)
async def handle_audio(message: types.Message, bot: Bot):
    chat_id = message.chat.id

    async with report_errors(bot, chat_id), heavy_job(message.from_user.id):
        # Уведомляем пользователя что всё идёт по плану
        waiting_message = await message.answer(text=WAITING_TEXT, parse_mode=ParseMode.HTML)
        try:
            with job_dir() as workdir:
                async with ChatActionSender(bot=bot, chat_id=chat_id, action=ChatAction.UPLOAD_VOICE):
                    # Расширение не указываем: аудио может быть в любом формате, FFmpeg определит его сам
                    source_path = workdir / "audio"
                    voice_path = workdir / "voice.ogg"
                    await download_tg_file(bot, message.audio.file_id, message.audio.file_size, source_path)

                    # Telegram корректно показывает голосовые только в OGG/Opus
                    await voice_from_media(source_path, voice_path)

                    # Отправляем обратно как voice
                    await message.reply_voice(voice=types.FSInputFile(path=voice_path),
                                              duration=message.audio.duration)
        finally:
            with suppress(TelegramAPIError):
                await waiting_message.delete()
