import os
from random import randint

from aiogram import Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from keyboards.video_processing_keyboard import VideoCdData
from modules.audio_defs import audio_from_video
from modules.video_defs import crop_video_to_square
from routers.video_processing import file_id_storage

router = Router(name=__name__)


@router.callback_query(VideoCdData.filter(F.operation == "note"))
async def video_for_note(call: CallbackQuery, callback_data: VideoCdData):
    message = call.message
    await call.answer()
    await message.delete()

    action_sender = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_VIDEO_NOTE,
    )

    action_recorder = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
        action=ChatAction.RECORD_VIDEO_NOTE,
    )

    async with action_recorder:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.RECORD_VIDEO_NOTE,
        )

    # Получаем объект файла
    try:
        file_id = file_id_storage.pop(callback_data.file_id, None)
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
    local_filename = f"downloads/{file_id}.mp4"

    # Формируем "соль" и добавляем её к имени конечного файла, чтобы не было никаких совпадений при множественном использовании в один момент времени
    sault = randint(0, 50000)
    output_path = local_filename[:-4] + f"{sault}.mp4"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    # Скачиваем файл
    await message.bot.download_file(file_path,
                                    destination=local_filename)

    successfull = await crop_video_to_square(local_filename, output_path)
    if successfull == False:
        duration_text = """⛔️ The bot can <b>ONLY</b> process videos <b>SHORTER than 60 seconds!</b>"""
        await message.answer(text=duration_text,
                             parse_mode=ParseMode.HTML)
        os.remove(local_filename)
        return

    waiting_text = """✅ I got it.  
    Please wait a moment..."""
    msg = await message.answer(text=waiting_text,
                               parse_mode=ParseMode.HTML)

    # Показываю что кружок уже загружается
    async with action_sender:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_VIDEO_NOTE,
        )

    # Отправляем обратно как video_note
    await message.answer_video_note(video_note=types.FSInputFile(path=output_path))

    await msg.delete()

    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)

@router.callback_query(VideoCdData.filter(F.operation == "voice"))
async def video_for_note(call: CallbackQuery, callback_data: VideoCdData):
    message = call.message
    await call.answer()
    await message.delete()

    action_sender = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
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

    # Получаем объект файла
    try:
        file_id = file_id_storage.pop(callback_data.file_id, None)
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
    local_filename = f"downloads/{file_id}.mp4"

    # Формируем "соль" и добавляем её к имени конечного файла, чтобы не было никаких совпадений при множественном использовании в один момент времени
    sault = randint(0, 50000)
    output_path = local_filename[:-4] + f"{sault}.mp3"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    # Скачиваем файл
    await message.bot.download_file(file_path,
                                    destination=local_filename
                                    )

    await audio_from_video(local_filename, output_path)

    waiting_text = """✅ I got it.  
    Please wait a moment..."""
    msg = await message.answer(text=waiting_text,
                               parse_mode=ParseMode.HTML)

    # Показываю что кружок уже загружается
    async with action_sender:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_VOICE,
        )

    # Отправляем обратно как voice
    await message.answer_voice(voice=types.FSInputFile(path=output_path))

    await msg.delete()

    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)


@router.callback_query(VideoCdData.filter(F.operation == "audio"))
async def video_for_note(call: CallbackQuery, callback_data: VideoCdData):
    message = call.message
    await call.answer()
    await message.delete()

    action_sender = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_DOCUMENT,
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

    # Получаем объект файла
    try:
        file_id = file_id_storage.pop(callback_data.file_id, None)
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
    local_filename = f"downloads/{file_id[:11]}.mp4"

    # Формируем "соль" и добавляем её к имени конечного файла, чтобы не было никаких совпадений при множественном использовании в один момент времени
    sault = randint(0, 50000)
    output_path = local_filename[:-4] + f"{sault}.mp3"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    # Скачиваем файл
    await message.bot.download_file(file_path,
                                    destination=local_filename
                                    )

    await audio_from_video(local_filename, output_path)

    waiting_text = """✅ I got it.  
        Please wait a moment..."""
    msg = await message.answer(text=waiting_text,
                               parse_mode=ParseMode.HTML)

    # Показываю что кружок уже загружается
    async with action_sender:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_DOCUMENT,
        )

    # Отправляем обратно как voice
    await message.answer_audio(audio=types.FSInputFile(path=output_path))

    await msg.delete()

    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)