import asyncio
import logging
import os

from aiogram.types import LinkPreviewOptions
from aiogram.utils import markdown
from aiogram.utils.chat_action import ChatActionSender
from decouple import config
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode, ChatAction


from aiogram.fsm.context import FSMContext

import ffmpeg
from random import randint

from states import Avangard, Vtovoice, Video_processing

bot_token = config('BOT_TOKEN')

bot = Bot(token=bot_token)
dp = Dispatcher()

def is_number(n):
    try:
        int(n)
        return True
    except ValueError:
        return False

# Функция старта
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    url ="https://sdmntpreastus2.oaiusercontent.com/files/00000000-60cc-51f6-9d6b-4c8d1e75ceac/raw?se=2025-04-05T14%3A13%3A54Z&sp=r&sv=2024-08-04&sr=b&scid=0dd2fe23-ebd7-5f9e-8874-d61e7e1e10ba&skoid=3f3a9132-9530-48ef-96b7-fee5a811733f&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-04-05T08%3A07%3A23Z&ske=2025-04-06T08%3A07%3A23Z&sks=b&skv=2024-08-04&sig=fTrYnU6l%2BLQVSzlNgFfmAmHuNkpq5rh0EGR4E5wjmic%3D"
    hello_text = f"""{markdown.hide_link(url)}👋 Hello, <b>{message.from_user.full_name}</b>!  
🎧 Welcome to the <b>Audio & Video Conversion Bot</b> 🔁

Here you can easily convert:  
🎵 <b>Audio files</b> → <i>Voice messages</i>  
🎬 <b>Video files</b> → <i>Video notes</i>
🎧 <b>Video notes</b> → <i>Voice messages</i>

❓ Type /help to learn how to use the bot.
"""
    old_text = f"{markdown.hide_link(url)}Hello, <b>{message.from_user.full_name}</b>! Welcome to the Audio to voice conversion tool. 🔁 📄\nIn this bot, you can easily convert audio and video files into voice and video messages, respectively.\n\n\nType'\help' to find out how to use it."
    await message.answer(text= hello_text,
                         parse_mode=ParseMode.HTML,
                         link_preview_options= LinkPreviewOptions(
                             is_disabled=False,
                             url=url,
                             show_above_text=True,
                         )
                    )



# Функция помощи
@dp.message(Command("help"))
async def handle_help(message: types.Message):
    help_text = """🔄 This bot converts:  
🎵 <b>MP3 audio files</b> → <i>Voice messages</i>  
🎬 <b>MP4 videos</b> → <i>Video notes</i>
🎧 <b>Video notes</b> → <i>Voice messages</i>

📤 Just upload your file and wait a moment while it's being converted.  
<b>Note:</b> Videos must be shorter than <b>60 seconds</b>.

🛠️ Want to convert <b>video notes</b> to <b>voice messages</b>?  
Use the command: /video_to_voice

⚠️ <b>ATTENTION!</b> Audio and video files must be under <b>20 MB</b>! ⚠️
"""
    await message.answer(text=help_text,
                         parse_mode=ParseMode.HTML)


# Функция Авангарда
@dp.message(Command("avangard"))
async def handle_avangard(message: types.Message, state: FSMContext):
    await state.set_state(Avangard.volume)
    avangard_text = """🔊 Please send me the <b>volume level</b> (e.g., <code>100</code> = 100%).
Just reply with a number."""

    await message.answer(text=avangard_text,
                         parse_mode=ParseMode.HTML)


@dp.message(Avangard.volume, F.text)
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


@dp.message(Avangard.volume)
async def invalid_volume(message: types.Message):
    invalid_text = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
    await message.answer(text=invalid_text,
                 parse_mode=ParseMode.HTML)


@dp.message(Avangard.song, F.text)
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


@dp.message(Avangard.song)
async def invalid_volume(message: types.Message):
    invalid_text = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
    await message.answer(text=invalid_text,
                 parse_mode=ParseMode.HTML)



@dp.message(F.video_note, Avangard.transforming)
async def avangard_note(message: types.VideoNote, state:FSMContext):
    # print(song, volume)
    songs = ["AVANGARD", "avangardik"]
    data = await state.get_data()
    max = len(songs) - 1
    song_number= data["song_num"] - 1
    # Устанавливаю потолок
    if song_number > max:
        song_number = max

    volume_parameter = data["volume_num"]
    audio_path = rf"C:\Users\bahamax\PycharmProjects\ConvertationBot\audio\{songs[song_number]}.mp3"
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
        file = await bot.get_file(file_id)
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
    await bot.download_file(file_path,
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


# Функция аудио из видео
@dp.message(Command("video_to_voice"))
async def handle_vtovoice(message: types.Message, state: FSMContext):
    await state.set_state(Vtovoice.getting_processing)
    test_text = """📹 Please send me a <b>video note</b>, and I will convert it to a voice message. 🎤"""

    await message.answer(text=test_text,
                         parse_mode=ParseMode.HTML)



@dp.message(F.video_note|F.video, Vtovoice.getting_processing)
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

    print("пытаюсь получить объект")
    # Получаем объект файла
    try:
        if message.video_note:
            file_id = message.video_note.file_id
        else:
            file_id = message.video.file_id
        file = await bot.get_file(file_id)

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
    await bot.download_file(file_path,
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



# Функция постоянной конвертации Аудио в ГС
@dp.message(F.audio)
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

    # Получаем объект файла
    try:
        file_id = message.audio.file_id
        file = await bot.get_file(file_id)
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
    await bot.download_file(file_path, destination=local_filename)



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


# Функция для добавления AVANGAARDD
async def avangard_video(input_path: str, output_path: str, audio_path: str, volume_parametr: int):
    """
    Добавляет к кружочку песенку AVANGARD.

    Args:
        input_path (str): Путь к входному видеофайлу.
        audio_path (str): Путь к добавляемому аудио.
        output_path (str): Путь для сохранения обработанного видеофайла.

    Raises:
        ffmpeg.Error: Если FFmpeg возвращает ошибку во время обработки.
    """
    # print("input_path:", input_path)
    print("exists:", os.path.exists(input_path))


    try:
        print(f"Начало обработки: видео='{input_path}', аудио='{audio_path}', вывод='{output_path}'")

        # Определяем входные потоки
        input_video = ffmpeg.input(input_path)
        input_audio = ffmpeg.input(audio_path)

        # Выбираем нужные потоки: видео из первого файла, аудио из обоих
        video_stream = input_video['v']  # Видеопоток из input_path
        original_audio = input_video['a']  # Аудиопоток из input_path
        audio_bob = input_audio['a']  # Аудиопоток из audio_path


        volumek = volume_parametr / 500
        external_audio = ffmpeg.filter(audio_bob, 'volume', volume=volumek)

        # Смешиваем два аудиопотока с помощью фильтра 'amix'
        # inputs=2 указывает, что на вход фильтра подается 2 потока
        # duration='first' - альтернатива -shortest, выбирает длительность первого потока
        # normalize=True - (опционально) нормализует громкость, чтобы избежать клиппинга
        mixed_audio = ffmpeg.filter(
            [original_audio, external_audio],
            'amix',
            inputs=2,
            duration='shortest'
            # duration='first', # Можно использовать 'first', 'shortest', 'longest'
            # normalize=True   # Раскомментируйте для нормализации громкости
        )

        # Собираем команду для FFmpeg
        # Мы берем видеопоток video_stream и смешанный аудиопоток mixed_audio


        # stream = ffmpeg.output(
        #     video_stream,  # Видео (копируем без перекодирования для скорости)
        #     mixed_audio,  # Смешанный звук (будет перекодирован)
        #     output_path,
        #     vcodec='copy',  # Копировать видео кодек (быстрее, если не нужно менять формат)
        #     acodec='aac',  # Выбрать аудио кодек (AAC - хороший стандарт)
        #     audio_bitrate='128k',  # Установить битрейт аудио (например, 192 kbps)
        #     shortest=True
        #     # Опция "-shortest": завершить обработку, когда закончится самый короткий входной поток (в нашем случае - видео)
        # )

        # Используем явное указание аргумента filename:
        stream = ffmpeg.output(
            video_stream,
            mixed_audio,
            filename=output_path,  # <-- Явно указываем имя файла
            vcodec='copy',
            acodec='aac',
            audio_bitrate='128k',
            # shortest=True
        )


        # Запускаем процесс FFmpeg
        # overwrite_output=True позволяет перезаписать файл, если он уже существует
        print("Запуск команды FFmpeg...")
        stdout, stderr = stream.run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

        # Можно раскомментировать для отладки вывода FFmpeg
        # print("FFmpeg stdout:", stdout.decode())
        # print("FFmpeg stderr:", stderr.decode())
        print(f"Обработка успешно завершена. Результат сохранен в '{output_path}'")

    except ffmpeg.Error as e:
        print('Ошибка при обработке видео:', e)
        if e.stderr:
            print('FFmpeg stderr:', e.stderr.decode('utf8', errors='ignore'))
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути '{input_path}'")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


# Функция для вытаскивания аудио из видео
async def audio_from_video(input_path: str, output_path: str):
    """
    Добавляет к кружочку песенку AVANGARD.

    Args:
        input_path (str): Путь к входному видеофайлу.
        output_path (str): Путь для сохранения обработанного видеофайла.

    Raises:
        ffmpeg.Error: Если FFmpeg возвращает ошибку во время обработки.
    """
    # print("input_path:", input_path)
    print("exists:", os.path.exists(input_path))


    try:
        print(f"Начало обработки: видео='{input_path}', вывод='{output_path}'")

        # Определяем входные потоки
        input_video = ffmpeg.input(input_path)

        # Выбираем нужные потоки: видео из первого файла, аудио
        video_stream = input_video['v']  # Видеопоток из input_path
        original_audio = input_video['a']  # Аудиопоток из input_path




        # Используем явное указание аргумента filename:
        stream = ffmpeg.output(

            original_audio,
            filename=output_path,  # <-- Явно указываем имя файла
            acodec='libmp3lame',
            audio_bitrate='128k',
            # shortest=True
        )


        # Запускаем процесс FFmpeg
        # overwrite_output=True позволяет перезаписать файл, если он уже существует
        print("Запуск команды FFmpeg...")
        stdout, stderr = stream.run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

        # Можно раскомментировать для отладки вывода FFmpeg
        # print("FFmpeg stdout:", stdout.decode())
        # print("FFmpeg stderr:", stderr.decode())
        print(f"Обработка успешно завершена. Результат сохранен в '{output_path}'")

    except ffmpeg.Error as e:
        print('Ошибка при обработке видео:', e)
        if e.stderr:
            print('FFmpeg stderr:', e.stderr.decode('utf8', errors='ignore'))
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути '{input_path}'")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

# Функция для обрезки видео в квадрат
async def crop_video_to_square(input_path: str, output_path: str):
    """
    Обрезает видео по центру до квадратной формы и уменьшает разрешение до 384x384.

    Args:
        input_path (str): Путь к входному видеофайлу.
        output_path (str): Путь для сохранения обработанного видеофайла.
    """
    print("input_path:", input_path)
    print("exists:", os.path.exists(input_path))

    try:
        probe = ffmpeg.probe(input_path)

        format_info = probe.get("format", {})
        duration = float(format_info.get("duration", 0))

        # Проверка на длительность
        if duration >= 60:
            print("❌ Видео слишком длинное:", duration, "секунд")
            return False


        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            print(f"Ошибка: Не найден видеопоток в файле '{input_path}'")
            return

        width = int(video_stream['width'])
        height = int(video_stream['height'])
        min_dim = min(width, height)
        offset_x = (width - min_dim) // 2
        offset_y = (height - min_dim) // 2

        crop_filter = f"crop={min_dim}:{min_dim}:{offset_x}:{offset_y},scale=384:384"

        (
            ffmpeg
            .input(input_path)
            .output(output_path,
                    vf=crop_filter,
                    vcodec="libx264",
                    acodec="aac",
                    audio_bitrate="128k",
                    format="mp4",
                    movflags="faststart")
            .run(overwrite_output=True)
        )

        print(f"Видео успешно обработано и сохранено в '{output_path}'")
        return True

    except ffmpeg.Error as e:
        print(f"Ошибка при обработке видео: {e.stderr.decode('utf8')}")
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути '{input_path}'")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")



# Функция постоянной конвертации Видео в Кружки
@dp.message(F.video)
async def handle_video_for_note(message: types.Video):
    # await message.bot.send_chat_action(
    #     chat_id=message.chat.id,
    #     action=ChatAction.UPLOAD_VOICE,
    # )
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
        file_id = message.video.file_id
        file = await bot.get_file(file_id)
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
    sault = randint(0,50000)
    output_path = local_filename[:-4] + f"{sault}.mp4"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    print("пытаюсь скачать")
    # Скачиваем файл
    await bot.download_file(file_path,
                            destination=local_filename
                            )

    print("готовлюсь обработать")
    successfull = await crop_video_to_square(local_filename, output_path)
    if successfull == False:
        print("Слишком многа")
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


    print("Пытаюсь отправить")
    # Отправляем обратно как video_note
    await message.answer_video_note(video_note=types.FSInputFile(path=output_path))

    await msg.delete()

    print("попытался отправить")
    # Удаляем файл
    os.remove(local_filename)
    os.remove(output_path)


# Функция ответа на случай непонимания со стороны пользователей
@dp.message(F.voice)
async def handle_for_voice(message: types.Audio):
    answer_voice = """⛔️ Please send an <b>AUDIO FILE</b>.  
I don't process voice messages."""
    await message.answer(text=answer_voice, parse_mode=ParseMode.HTML)

@dp.message(F.video_note)
async def handle_for_voice(message: types.VideoNote):
    answer_video_note = """⛔️ Please send just an ordinary <b>VIDEO</b>.  
I don't process video notes."""
    await message.answer(text=answer_video_note, parse_mode=ParseMode.HTML)
"""
Эти функции объясняют пользователю какого типа сообщения нужно отправлять
чтобы бот их обработал, на случай если пользователь перепутал и отправил ГС или Кружок
"""


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())