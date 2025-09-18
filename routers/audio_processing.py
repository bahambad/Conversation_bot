import os


from aiogram import Router, types, F
from aiogram.enums import ParseMode, ChatAction

from aiogram.utils.chat_action import ChatActionSender


router = Router(name=__name__)


# Функция постоянной конвертации Аудио в ГС
@router.message(F.audio)
async def handle_audio(message: types.Audio):
    action_sender = ChatActionSender(
        bot = message.bot,
        chat_id= message.chat.id,
        action=ChatAction.UPLOAD_VOICE,
    )
    action_recorder = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
        action=ChatAction.RECORD_VOICE,
    )
    async with action_recorder:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.RECORD_VOICE,
        )

    # bot = message.bot
    # Получаем объект файла
    try:
        file_id = message.audio.file_id
        file = await message.bot.get_file(file_id)
    except:
        error_text = (f"""⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
                      # f"\nError: {e}"
                      )
        await message.answer(text=error_text,
                             parse_mode=ParseMode.HTML)
        return


    # Формируем путь для сохранения
    file_path = file.file_path
    local_filename = f"downloads/{file_id}.mp3"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    # Скачиваем файл
    await message.bot.download_file(file_path, destination=local_filename)



    # Уведомляем пользователя что всё идёт по плану
    waiting_text = """✅ I got it.  
Please wait a moment..."""
    msg = await message.answer(text=waiting_text,
                         parse_mode=ParseMode.HTML)

    async with action_sender:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_VOICE,
        )

    # Отправляем обратно как voice
    await message.reply_voice(voice=types.FSInputFile(path=local_filename))

    await msg.delete()

    # Удаляем файл
    os.remove(local_filename)