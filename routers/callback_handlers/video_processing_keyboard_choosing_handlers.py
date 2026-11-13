from contextlib import suppress

from aiogram import Bot, Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from keyboards.video_processing_keyboard import VideoCdData
from modules.audio_defs import audio_from_video, voice_from_media
from modules.jobs import download_tg_file, heavy_job, job_dir, report_errors
from modules.permissions import is_privileged
from modules.video_defs import crop_video_to_square
from routers.callback_handlers.common import claim_entry
from routers.video_processing import file_id_storage

router = Router(name=__name__)

WAITING_TEXT = "✅ I got it.\nPlease wait a moment..."
NOTE_FORBIDDEN_TEXT = "⛔️ Video notes are not available for you."

# Какой статус показывать в чате, пока выполняется операция
CHAT_ACTIONS = {
    "note": ChatAction.UPLOAD_VIDEO_NOTE,
    "voice": ChatAction.UPLOAD_VOICE,
    "audio": ChatAction.UPLOAD_DOCUMENT,
}


# Один обработчик на все операции с видео: кружок, голосовое сообщение, MP3
@router.callback_query(VideoCdData.filter(F.operation.in_(set(CHAT_ACTIONS))))
async def process_video(call: CallbackQuery, callback_data: VideoCdData, bot: Bot):
    operation = callback_data.operation
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    keyboard_message_id = call.message.message_id

    # Кнопки кружка у остальных пользователей нет, но callback_data можно подделать — проверяем ещё раз
    if operation == "note" and not is_privileged(user_id):
        await call.answer(NOTE_FORBIDDEN_TEXT, show_alert=True)
        return

    entry = await claim_entry(call, bot, file_id_storage, callback_data.file_id)
    if entry is None:
        return

    async with report_errors(bot, chat_id):
        async with heavy_job(user_id):
            await call.answer()
            with suppress(TelegramAPIError):
                await bot.delete_message(chat_id, keyboard_message_id)

            waiting_message = await bot.send_message(chat_id, WAITING_TEXT, parse_mode=ParseMode.HTML)
            try:
                with job_dir() as workdir:
                    async with ChatActionSender(bot=bot, chat_id=chat_id, action=CHAT_ACTIONS[operation]):
                        source_path = workdir / "input.mp4"
                        await download_tg_file(bot, entry.file_id, entry.file_size, source_path)

                        if operation == "note":
                            output_path = workdir / "note.mp4"
                            await crop_video_to_square(source_path, output_path)
                            await bot.send_video_note(chat_id, video_note=types.FSInputFile(path=output_path))
                        elif operation == "voice":
                            output_path = workdir / "voice.ogg"
                            await voice_from_media(source_path, output_path)
                            await bot.send_voice(chat_id, voice=types.FSInputFile(path=output_path),
                                                 duration=entry.duration)
                        else:
                            output_path = workdir / "audio.mp3"
                            await audio_from_video(source_path, output_path)
                            await bot.send_audio(chat_id, audio=types.FSInputFile(path=output_path))
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()
