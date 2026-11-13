from contextlib import suppress

from aiogram import Bot, Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.chat_action import ChatActionSender

from modules.jobs import download_tg_file, job_dir, report_errors

router = Router(name=__name__)

WAITING_TEXT = "✅ I got it.\nPlease wait a moment..."


# Функция постоянной конвертации Аудио в ГС
@router.message(F.audio)
async def handle_audio(message: types.Message, bot: Bot):
    chat_id = message.chat.id

    async with report_errors(bot, chat_id):
        # Уведомляем пользователя что всё идёт по плану
        waiting_message = await message.answer(text=WAITING_TEXT, parse_mode=ParseMode.HTML)
        try:
            with job_dir() as workdir:
                async with ChatActionSender(bot=bot, chat_id=chat_id, action=ChatAction.UPLOAD_VOICE):
                    local_path = workdir / "audio.mp3"
                    await download_tg_file(bot, message.audio.file_id, message.audio.file_size, local_path)

                    # Отправляем обратно как voice
                    await message.reply_voice(voice=types.FSInputFile(path=local_path))
        finally:
            with suppress(TelegramAPIError):
                await waiting_message.delete()
