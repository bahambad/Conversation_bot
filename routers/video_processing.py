from dataclasses import dataclass

from aiogram import Router, F, types
from aiogram.enums import ParseMode

from keyboards.video_processing_keyboard import builder_video_processing_kb_cb
from keyboards.yt_dlp_keyboard import builder_video_processing_cb
from modules.errors import FileTooBigError, UnsupportedUrlError
from modules.jobs import MAX_FILE_SIZE
from modules.permissions import can_make_video_notes
from modules.storage import TTLStore
from modules.yt_downloads import validate_url


router = Router(name=__name__)


@dataclass
class FileEntry:
    file_id: str
    file_size: int | None
    user_id: int
    duration: int | None = None


@dataclass
class UrlEntry:
    url: str
    user_id: int


# Файлы и ссылки, ожидающие выбора операции на inline-клавиатуре
file_id_storage: TTLStore[FileEntry] = TTLStore()
url_storage: TTLStore[UrlEntry] = TTLStore()


# Функция постоянной конвертации Видео в Кружки
@router.message(F.video_note | F.video)
async def handle_video(message: types.Message):
    media = message.video_note or message.video
    # Кружок имеет смысл делать только из обычного видео и только тем, кому это разрешено
    allow_note = message.video is not None and can_make_video_notes(message.from_user.id)

    # Bot API не отдаёт файлы больше 20 МБ, поэтому сообщаем об этом сразу
    if media.file_size is not None and media.file_size > MAX_FILE_SIZE:
        await message.answer(text=FileTooBigError.text, parse_mode=ParseMode.HTML)
        return

    file_dict_id = file_id_storage.put(FileEntry(
        file_id=media.file_id,
        file_size=media.file_size,
        user_id=message.from_user.id,
        duration=media.duration,
    ))

    await message.answer(text="Okay! What would you like to do with this video? 🎬",
                         parse_mode=ParseMode.HTML,
                         reply_markup=builder_video_processing_kb_cb(file_id=file_dict_id, allow_note=allow_note),
                         )


# Функция скачивания видео или аудио по ссылке
@router.message(F.text.startswith("https://"))
async def download_video_or_audio(message: types.Message):
    # Принимаем только одиночные ссылки на разрешённые сайты
    try:
        url = validate_url(message.text)
    except UnsupportedUrlError as e:
        await message.answer(text=e.text, parse_mode=ParseMode.HTML)
        return

    url_id = url_storage.put(UrlEntry(url=url, user_id=message.from_user.id))

    await message.answer(text="Okay! What would you like to download?",
                         parse_mode=ParseMode.HTML,
                         reply_markup=builder_video_processing_cb(url_id=url_id),
                         )
