from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from decouple import config

from ..filters.is_admin import IsAdmin


admin_id = int(config('ADMIN'))
admin_router = Router(name="Admin Router")
admin_router.message.filter(IsAdmin(admin_id))
# Хранится только в памяти: после рестарта список намеренно очищается.
ban_list: set[int] = set()


def _parse_user_id(command: CommandObject) -> int | None:
    """Достаёт id пользователя из аргумента команды, None — если аргумент некорректен."""
    args = (command.args or "").strip()
    try:
        return int(args)
    except ValueError:
        return None


@admin_router.message(Command("ban"))
async def ban_command(message: types.Message, command: CommandObject):
    ban_user = _parse_user_id(command)
    if ban_user is None:
        await message.answer("Usage: /ban <user_id>")
        return
    if ban_user == admin_id:
        await message.answer("You can't ban yourself dumbo")
        return
    ban_list.add(ban_user)
    await message.answer(f"User {ban_user} is banned! >:))")


@admin_router.message(Command("unban"))
async def unban_command(message: types.Message, command: CommandObject):
    ban_user = _parse_user_id(command)
    if ban_user is None:
        await message.answer("Usage: /unban <user_id>")
        return
    if ban_user not in ban_list:
        await message.answer(f"User {ban_user} is not banned")
        return
    ban_list.discard(ban_user)
    await message.answer(f"User {ban_user} is unbanned! <3")


@admin_router.message(Command("check"))
async def check_ban(message: types.Message):
    text = "Banned users:"
    for usr in sorted(ban_list):
        text += f"\n{usr}"
    text += "\n\nThat's all!"
    await message.answer(text)
