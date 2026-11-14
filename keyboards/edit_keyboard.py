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
