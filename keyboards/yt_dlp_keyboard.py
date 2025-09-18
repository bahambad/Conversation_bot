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

def builder_video_processing_cb(url_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Video",
                   callback_data=UrlOfVideoCdData(url_id=url_id, operation="video").pack(),
                   )
    builder.button(text="🎵 Audio",
                   callback_data=UrlOfVideoCdData(url_id=url_id, operation="audio").pack(),
                   )

    return builder.as_markup()