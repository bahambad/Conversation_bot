import uuid


from aiogram import Router, F, types
from aiogram.enums import ParseMode

from keyboards.video_processing_keyboard import builder_video_processing_kb_cb

from keyboards.yt_dlp_keyboard import builder_video_processing_cb


router = Router(name=__name__)

# dicts of urls (tmp)
url_storage = {}
file_id_storage = {}


# Функция постоянной конвертации Видео в Кружки
@router.message(F.video_note|F.video)
async def handle_video(message: types.Video):
    text = "Okay! What would you like to do with this video? 🎬"
    is_video = False

    try:
        # генерируем уникальный id для словаря
        file_dict_id = str(uuid.uuid4())
        if message.video_note:
            # сохраняем ссылку в словарь
            file_id_storage[file_dict_id] = message.video_note.file_id
        else:
            file_id_storage[file_dict_id] = message.video.file_id
            is_video = True
    except:
        error_text = (f"""⛔️ <b>Failed to receive the file.</b>  
        The file is too big. Please upload a file smaller than <b>20 MB</b>."""
                      # f"\nError: {e}"
                      )
        await message.answer(text=error_text,
                             parse_mode=ParseMode.HTML)
        return

    await message.answer(text=text,
                         parse_mode=ParseMode.HTML,
                         reply_markup=builder_video_processing_kb_cb(file_id=file_dict_id, is_video=is_video),
                         )


# Функция скачивания видео или аудио по ссылке
@router.message(F.text.startswith("https://"))
async def download_video_or_audio(message: types.Message):
    text = """Okay! What would you like to download?"""

    # генерируем уникальный id
    url_id = str(uuid.uuid4())
    # сохраняем ссылку в словарь
    url_storage[url_id] = message.text

    await message.answer(text=text,
                         parse_mode=ParseMode.HTML,
                         reply_markup=builder_video_processing_cb(url_id=url_id),
                         )