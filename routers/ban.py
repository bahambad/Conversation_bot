from aiogram import Router, types

from .filters.is_banned import IsBanned

router = Router(name=__name__)

BANNED_TEXT = "Этот бот только для людей, у которых есть совесть"


@router.message(IsBanned())
async def banned_user_handler(message: types.Message):
    await message.answer(BANNED_TEXT)


# Без этого забаненный мог бы продолжать пользоваться уже выданными кнопками
@router.callback_query(IsBanned())
async def banned_user_callback_handler(call: types.CallbackQuery):
    await call.answer(BANNED_TEXT, show_alert=True)
