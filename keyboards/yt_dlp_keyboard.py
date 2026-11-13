from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


class UrlOfVideoCdData(CallbackData, prefix="url-video-str"):
    url_id: str
    operation: str


def builder_video_processing_choose_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎬 Video")
    builder.button(text="🎵 Audio")

    return builder.as_markup(resize_keyboard=True)

def builder_video_processing_cb(url_id, allow_fragment: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Video",
                   callback_data=UrlOfVideoCdData(url_id=url_id, operation="video").pack(),
                   )
    builder.button(text="🎵 Audio",
                   callback_data=UrlOfVideoCdData(url_id=url_id, operation="audio").pack(),
                   )
    # Экспериментальная функция: скачивание фрагмента по таймкодам, кнопки видит только админ.
    # Второй ряд повторяет первый: видео слева, аудио справа.
    if allow_fragment:
        builder.button(text="✂️ Video part",
                       callback_data=UrlOfVideoCdData(url_id=url_id, operation="fragment").pack(),
                       )
        builder.button(text="✂️ Audio part",
                       callback_data=UrlOfVideoCdData(url_id=url_id, operation="fragment_audio").pack(),
                       )
    builder.adjust(2)

    return builder.as_markup()