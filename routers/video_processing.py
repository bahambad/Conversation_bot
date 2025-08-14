import os
from random import randint

from aiogram import Router, F, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.chat_action import ChatActionSender
from aiogram.fsm.context import FSMContext

# from config import bot
from modules.video_defs import crop_video_to_square
from modules.yt_downloads import download_video_from_youtube, download_audio_from_youtube, check_video_size
from states import DownloadFromLink
from keyboards.yt_dlp_keyboard import builder_video_processing_choose_keyboard

router = Router(name=__name__)

# Функция постоянной конвертации Видео в Кружки
@router.message(F.video)
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
    # bot = message.bot

    print("пытаюсь получить объект")
    # Получаем объект файла
    try:
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
    output_path = local_filename[:-4] + f"{sault}.mp4"

    # Убедимся, что папка существует
    os.makedirs("downloads", exist_ok=True)

    print("пытаюсь скачать")
    # Скачиваем файл
    await message.bot.download_file(file_path,
                            destination=local_filename)

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


# Функция скачивания видео или аудио по ссылке
@router.message(F.text.startswith("https://"))
async def download_video_or_audio(message: types.Message,  state: FSMContext):
    await state.set_state(DownloadFromLink.choosing_type)
    text = """Okay! What do you want to download? Audio or video?"""
    await state.update_data(url=str(message.text))
    await message.answer(text=text,
                         parse_mode=ParseMode.HTML,
                         reply_markup=builder_video_processing_choose_keyboard(),
                         )

@router.message(DownloadFromLink.choosing_type, F.text)
async def type_of_download(message: types.Message, state:FSMContext):
    if message.text.lower() == "audio":
        text = """Okay, i got it. Now i'm going to download audio from this video"""
        msg = await message.answer(text=text,
                                   parse_mode=ParseMode.HTML,
                                   reply_markup=ReplyKeyboardRemove(),
                                   )

        action_sender = ChatActionSender(
            bot=message.bot,
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_DOCUMENT,
        )
        data = await state.get_data()
        url = data["url"]
        if check_video_size(url, 1080, max_size_mb=20):
            try:
                outpath = download_audio_from_youtube(url)
                if outpath == False:
                    error_text = "Error. I can't download it for some reason."
                    await message.answer(text=error_text,
                                         parse_mode=ParseMode.HTML,
                                         )
                    await state.clear()
                    await msg.delete()
                    return
                # Показываю что видео уже загружается
                async with action_sender:
                    await message.bot.send_chat_action(
                        chat_id=message.chat.id,
                        action=ChatAction.UPLOAD_DOCUMENT,
                    )

                # Отправляем аудио
                await message.reply_audio(audio=types.FSInputFile(path=outpath))

                await msg.delete()
                await state.clear()
                os.remove(outpath)

            except:
                error_text = """⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
                await message.answer(text=error_text,
                                     parse_mode=ParseMode.HTML)
                await msg.delete()
                await state.clear()
                return

        else:
            big_video_text = """⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
            await message.answer(text=big_video_text,
                                 parse_mode=ParseMode.HTML)
            await msg.delete()
            await state.clear()
            return

    elif message.text.lower() == "video":
        text = """Okay, i got it. Now i'm going to download this video"""
        msg = await message.answer(text=text,
                                   parse_mode=ParseMode.HTML,
                                   )
        action_sender = ChatActionSender(
            bot=message.bot,
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_VIDEO,
        )
        data = await state.get_data()
        url = data["url"]
        size_okay = check_video_size(url, 1080, max_size_mb=20)
        if size_okay:
            try:
                outpath = download_video_from_youtube(url)
                if outpath == False:
                    error_text = "Error. I can't download it for some reason."
                    await message.answer(text=error_text,
                                         parse_mode=ParseMode.HTML, )
                    await state.clear()
                    await msg.delete()
                    return
                    # Показываю что видео уже загружается
                async with action_sender:
                    await message.bot.send_chat_action(
                        chat_id=message.chat.id,
                        action=ChatAction.UPLOAD_VIDEO,
                    )

                # Отправляем аудио
                await message.reply_video(video=types.FSInputFile(path=outpath))

                await msg.delete()
                await state.clear()
                os.remove(outpath)

            except:
                error_text = """⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
                await message.answer(text=error_text,
                                     parse_mode=ParseMode.HTML)
                await msg.delete()
                await state.clear()
                return
        else:
            big_video_text = """⛔️ <b>Failed to receive the file.</b>  
The file is too big. Please upload a file smaller than <b>20 MB</b>."""
            await message.answer(text=big_video_text,
                                 parse_mode=ParseMode.HTML)
            await msg.delete()
            await state.clear()
            return

    else:
        invalid_text = """<b>Please send word.</b>
I didn’t understand your response — just reply with a word."""
        await message.answer(text=invalid_text,
                             parse_mode=ParseMode.HTML)
        await state.clear()
