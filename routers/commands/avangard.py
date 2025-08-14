import os
from random import randint

from aiogram import Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender
# from config import bot

from modules.avangard_defs import avangard_video, is_number
from states import Avangard

router = Router(name=__name__)

# Функция Авангарда
@router.message(Command("avangard"))
async def handle_avangard(message: types.Message, state: FSMContext):
    await state.set_state(Avangard.volume)
    avangard_text = """🔊 Please send me the <b>volume level</b> (e.g., <code>100</code> = 100%).
Just reply with a number."""

    await message.answer(text=avangard_text,
                         parse_mode=ParseMode.HTML)


@router.message(Avangard.volume, F.text)
async def volume(message: types.Message, state:FSMContext):

    if is_number(message.text):

        await state.set_state(Avangard.song)

        await state.update_data(volume_num=int(message.text))
        song_text = """🎵 Okay, I got it!
Now, which song do you want?

Please send:
<code>1</code> — for the <b>first</b> song
<code>2</code> — for the <b>second</b> song

Just reply with the number."""
        await message.answer(text=song_text,
                     parse_mode=ParseMode.HTML)
    else:
        invalid_text = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
        await message.answer(text=invalid_text,
                             parse_mode=ParseMode.HTML)


@router.message(Avangard.volume)
async def invalid_volume(message: types.Message):
    invalid_text = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
    await message.answer(text=invalid_text,
                 parse_mode=ParseMode.HTML)


@router.message(Avangard.song, F.text)
async def song(message: types.Message, state:FSMContext):

    if is_number(message.text):

        await state.set_state(Avangard.transforming)

        await state.update_data(song_num=int(message.text))
        song_text = """✅ Okay, I got it.  
📹 Now send me a <b>video note</b> to transform it into a voice message."""
        await message.answer(text=song_text,
                     parse_mode=ParseMode.HTML)
    else:
        invalid_text = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
        await message.answer(text=invalid_text,
                             parse_mode=ParseMode.HTML)


@router.message(Avangard.song)
async def invalid_song(message: types.Message):
    invalid_text = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
    await message.answer(text=invalid_text,
                 parse_mode=ParseMode.HTML)


@router.message(F.video_note, Avangard.transforming)
async def avangard_note(message: types.VideoNote, state:FSMContext):
    # print(song, volume)
    songs = ["AVANGARD", "avangardik"]
    data = await state.get_data()
    max = len(songs) - 1
    song_number= data["song_num"] - 1
    # Устанавливаю потолок
    if song_number > max:
        song_number = max
    if song_number <0:
        song_number = 0

    volume_parameter = data["volume_num"]
    audio_path = rf"/home/babah/ConvertationBot/audio/{songs[song_number]}.mp3"
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

    print("пытаюсь получить объект")
    # Получаем объект файла
    try:
        file_id = message.video_note.file_id
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
    output_path = local_filename[:-4] + f"{sault}.mp4"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    print("пытаюсь скачать")
    # Скачиваем файл
    await message.bot.download_file(file_path,
                            destination=local_filename
                            )

    print("готовлюсь обработать")
    await avangard_video(local_filename, output_path, audio_path, volume_parameter)
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
            action=ChatAction.UPLOAD_VIDEO_NOTE,
        )

    print("Пытаюсь отправить")
    # Отправляем обратно как video_note
    await message.answer_video_note(video_note=types.FSInputFile(path=output_path))

    await msg.delete()
    await state.clear()

    print("попытался отправить")
    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)
