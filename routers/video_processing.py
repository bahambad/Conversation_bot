import uuid
from dataclasses import dataclass

from aiogram import Router, F, types
from aiogram.enums import ParseMode

from keyboards.video_processing_keyboard import builder_video_processing_kb_cb
from keyboards.yt_dlp_keyboard import builder_video_processing_cb
from modules.errors import FileTooBigError
from modules.jobs import MAX_FILE_SIZE
from modules.storage import TTLStore


router = Router(name=__name__)


@dataclass
class FileEntry:
    file_id: str
    file_size: int | None
    user_id: int


# dict of urls (tmp)
url_storage = {}
# Файлы, ожидающие выбора операции на inline-клавиатуре
file_id_storage: TTLStore[FileEntry] = TTLStore()


# Функция постоянной конвертации Видео в Кружки
@router.message(F.video_note | F.video)
async def handle_video(message: types.Message):
    media = message.video_note or message.video
    is_video = message.video is not None

    # Bot API не отдаёт файлы больше 20 МБ, поэтому сообщаем об этом сразу
    if media.file_size is not None and media.file_size > MAX_FILE_SIZE:
        await message.answer(text=FileTooBigError.text, parse_mode=ParseMode.HTML)
        return

    file_dict_id = file_id_storage.put(FileEntry(
        file_id=media.file_id,
        file_size=media.file_size,
        user_id=message.from_user.id,
    ))

    await message.answer(text="Okay! What would you like to do with this video? 🎬",
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
