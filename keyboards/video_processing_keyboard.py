from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class VideoCdData(CallbackData, prefix="video-proces-str"):
    operation: str
    file_id: str


def builder_video_processing_kb_cb(file_id, is_video) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # if is_video:
    #     builder.button(text="🎥 Video note",
    #                    callback_data=VideoCdData(operation="note", file_id=file_id).pack(),
    #                    ) #Временно недоступно
    builder.button(text="🎤 Voice message",
                   callback_data=VideoCdData(operation="voice", file_id=file_id).pack(),
                   )
    builder.button(text="🎵 Audio (MP3)",
                   callback_data=VideoCdData(operation="audio", file_id=file_id).pack(),
                   )
    builder.adjust(2)

    return builder.as_markup()