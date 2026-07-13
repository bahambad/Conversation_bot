
from aiogram.types import Message
from aiogram import Router, types
from aiogram.filters import Command
from decouple import config

from ..filters.is_admin import IsAdmin



admin_id = int(config('ADMIN'))
admin_router = Router(name="Admin Router")
admin_router.message.filter(IsAdmin(admin_id))
ban_list = []

@admin_router.message(Command("ban"))
async def ban_command(message: types.Message):
    ban_user = int(message.text.split(' ', 1)[1])
    if ban_user != admin_id:
        ban_list.append(ban_user)
        await message.answer(f"User {ban_user} is banned! >:))")
    else:
        await message.answer("You can't ban yourself dumbo")


@admin_router.message(Command("unban"))
async def unban_command(message: types.Message):
    ban_user = int(message.text.split(' ', 1)[1])
    if ban_user in ban_list:
        ban_list.remove(ban_user)
    await message.answer(f"User {ban_user} is unbanned! <3")

@admin_router.message(Command("check"))
async def check_ban(message: types.Message):
    text = "Banned users:"
    for usr in ban_list:
        text += f"\n{usr}"
    text+= "\n\nThat's all!"
    await message.answer(text)