from contextlib import suppress

from aiogram import Bot, Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from keyboards.video_processing_keyboard import VideoCdData
from modules.audio_defs import audio_from_video
from modules.jobs import download_tg_file, heavy_job, is_busy, job_dir, report_errors
from modules.video_defs import crop_video_to_square
from routers.video_processing import file_id_storage

router = Router(name=__name__)

EXPIRED_TEXT = "⌛️ This button has expired. Please send the file again."
NOT_YOURS_TEXT = "This button is for the person who sent the file."
BUSY_ALERT_TEXT = "⏳ Your previous request is still being processed. Please wait."
WAITING_TEXT = "✅ I got it.\nPlease wait a moment..."

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

    entry = file_id_storage.get(callback_data.file_id)
    if entry is None:
        await call.answer(EXPIRED_TEXT, show_alert=True)
        with suppress(TelegramAPIError):
            await bot.delete_message(chat_id, keyboard_message_id)
        return
    if entry.user_id != user_id:
        await call.answer(NOT_YOURS_TEXT, show_alert=True)
        return
    if is_busy(user_id):
        # Кнопку не трогаем: ей можно будет воспользоваться, когда закончится предыдущая задача
        await call.answer(BUSY_ALERT_TEXT, show_alert=True)
        return
    file_id_storage.pop(callback_data.file_id)

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
                            output_path = workdir / "voice.mp3"
                            await audio_from_video(source_path, output_path)
                            await bot.send_voice(chat_id, voice=types.FSInputFile(path=output_path))
                        else:
                            output_path = workdir / "audio.mp3"
                            await audio_from_video(source_path, output_path)
                            await bot.send_audio(chat_id, audio=types.FSInputFile(path=output_path))
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()
