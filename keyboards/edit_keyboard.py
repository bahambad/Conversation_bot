from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class EditCdData(CallbackData, prefix="edit"):
    action: str  # "run" или "cancel"
    plan_id: int


def builder_edit_plan_kb(plan_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Run", callback_data=EditCdData(action="run", plan_id=plan_id).pack())
    builder.button(text="✖️ Cancel", callback_data=EditCdData(action="cancel", plan_id=plan_id).pack())
    return builder.as_markup()


class EditLinkCdData(CallbackData, prefix="editlink"):
    link_id: int
    audio: bool
    part: bool  # True — фрагмент по таймкодам, False — запись целиком


def builder_edit_link_kb(link_id: int, has_range: bool) -> InlineKeyboardMarkup:
    """Что взять из ссылки. Если таймкоды уже указаны в сообщении, остаётся выбрать видео или аудио."""
    builder = InlineKeyboardBuilder()
    if has_range:
        builder.button(text="✂️ Video part", callback_data=EditLinkCdData(link_id=link_id, audio=False, part=True).pack())
        builder.button(text="✂️ Audio part", callback_data=EditLinkCdData(link_id=link_id, audio=True, part=True).pack())
    else:
        builder.button(text="🎬 Video", callback_data=EditLinkCdData(link_id=link_id, audio=False, part=False).pack())
        builder.button(text="🎵 Audio", callback_data=EditLinkCdData(link_id=link_id, audio=True, part=False).pack())
        builder.button(text="✂️ Video part", callback_data=EditLinkCdData(link_id=link_id, audio=False, part=True).pack())
        builder.button(text="✂️ Audio part", callback_data=EditLinkCdData(link_id=link_id, audio=True, part=True).pack())
    builder.adjust(2)
    return builder.as_markup()
