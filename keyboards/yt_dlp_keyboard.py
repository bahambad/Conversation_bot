from aiogram.utils.keyboard import ReplyKeyboardBuilder


def builder_video_processing_choose_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Video")
    builder.button(text="Audio")

    return builder.as_markup(resize_keyboard=True)