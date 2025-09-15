import os
from random import randint

from aiogram import Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender
# from config import bot

from modules.audio_defs import audio_from_video
from states import Vtovoice

router = Router(name=__name__)

# Функция аудио из видео
@router.message(Command("video_to_voice"))
async def handle_vtovoice(message: types.Message, state: FSMContext):
    await state.set_state(Vtovoice.getting_processing)
    test_text = """📹 Please send me a <b>video note</b>, and I will convert it to a voice message. 🎤"""

    await message.answer(text=test_text,
                         parse_mode=ParseMode.HTML)


@router.message(F.video_note|F.video, Vtovoice.getting_processing)
async def video_to_voice_processing(message: types.VideoNote, state:FSMContext):

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

    # bot = message.bot
    print("пытаюсь получить объект")
    # Получаем объект файла
    try:
        if message.video_note:
            file_id = message.video_note.file_id
        else:
            file_id = message.video.file_id
        file = await message.bot.get_file(file_id)

    except:
        error_text = (f"""⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
                      # f"\nError: {e}"
                      )
        await message.answer(text=error_text,
                             parse_mode=ParseMode.HTML)
        return

    print("пытаюсь сохранить")
    # Формируем путь для сохранения
    file_path = file.file_path
    local_filename = f"downloads/{file_id}.mp4"

    # Формируем "соль" и добавляем её к имени конечного файла, чтобы не было никаких совпадений при множественном использовании в один момент времени
    sault = randint(0, 50000)
    output_path = local_filename[:-4] + f"{sault}.mp3"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    print("пытаюсь скачать")
    # Скачиваем файл
    await message.bot.download_file(file_path,
                            destination=local_filename
                            )

    print("готовлюсь обработать")
    await audio_from_video(local_filename, output_path)
    # if successfull == False:
    #     print("Слишком многа")
    #     duration_text = """⛔️The bot can <b>ONLY</b> process videos <b>SHORTER than 60 seconds!</b>⛔️"""
    #     await message.answer(text=duration_text,
    #                          parse_mode=ParseMode.HTML)
    #     os.remove(local_filename)
    #     return

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

    print("Пытаюсь отправить")
    # Отправляем обратно как voice
    await message.reply_voice(voice=types.FSInputFile(path=output_path))

    await msg.delete()
    await state.clear()

    print("попытался отправить")
    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)



# Функция mp3 из видео
@router.message(Command("mp4_to_mp3"))
async def handle_vtomp3(message: types.Message, state: FSMContext):
    # await state.set_state(Vtovoice.getting_processing)
    test_text = """📹 Please send me a <b>video note</b>, and I will convert it to a mp3 audio. 🎤"""

    await message.answer(text=test_text,
                         parse_mode=ParseMode.HTML)


@router.message(F.video_note|F.video, Vtovoice.getting_processing)
async def video_to_mp3_processing(message: types.VideoNote, state:FSMContext):

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

    # bot = message.bot
    print("пытаюсь получить объект")
    # Получаем объект файла
    try:
        if message.video_note:
            file_id = message.video_note.file_id
        else:
            file_id = message.video.file_id
        file = await message.bot.get_file(file_id)

    except:
        error_text = (f"""⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
                      # f"\nError: {e}"
                      )
        await message.answer(text=error_text,
                             parse_mode=ParseMode.HTML)
        return

    print("пытаюсь сохранить")
    # Формируем путь для сохранения
    file_path = file.file_path
    local_filename = f"downloads/{file_id}.mp4"

    # Формируем "соль" и добавляем её к имени конечного файла, чтобы не было никаких совпадений при множественном использовании в один момент времени
    sault = randint(0, 50000)
    output_path = local_filename[:-4] + f"{sault}.mp3"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    print("пытаюсь скачать")
    # Скачиваем файл
    await message.bot.download_file(file_path,
                            destination=local_filename
                            )

    print("готовлюсь обработать")
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

    print("Пытаюсь отправить")
    # Отправляем обратно как voice
    await message.reply_audio(audio=types.FSInputFile(path=output_path))

    await msg.delete()
    # await state.clear()

    print("попытался отправить")
    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)


# Функция постоянной конвертации Аудио в ГС
@router.message(F.audio)
async def handle_audio(message: types.Audio):
    # await message.bot.send_chat_action(
    #     chat_id=message.chat.id,
    #     action=ChatAction.UPLOAD_VOICE,
    # )
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

    async with action_recorder:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_VOICE,
        )

    # Отправляем обратно как voice
    await message.reply_voice(voice=types.FSInputFile(path=local_filename))

    await msg.delete()

    # Удаляем файл
    os.remove(local_filename)
