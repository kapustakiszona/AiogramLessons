from aiogram import Router, F
from aiogram.types import Message

from create_bot import admins, users_data

router = Router()

# Хендлер для кнопки "Администрирование"
@router.message(F.text == "Администрирование")
async def admin_panel(message: Message):
    user_id = message.chat.id
    if user_id in admins:
        admin_text = (
            "Вы вошли в панель администратора. Доступные команды:\n"
            "/view_users - Показать всех пользователей\n"
            "/grant_premium - Предоставить премиум-доступ пользователю\n"
            "/remove_user - Удалить пользователя"
        )
        await message.answer(admin_text)
    else:
        await message.answer("У вас нет прав администратора.")


# Хендлер для команды /view_users
@router.message(F.text.startswith("/view_users"))
async def view_users(message: Message):
    user_id = message.chat.id
    if user_id in admins:
        user_list = "\n".join([f"User ID: {uid}, Premium: {data['is_premium']}" for uid, data in users_data.items()])
        await message.answer(f"Список всех пользователей:\n{user_list}")
    else:
        await message.answer("У вас нет прав администратора.")


# Хендлер для команды /grant_premium
@router.message(F.text.startswith("/grant_premium"))
async def grant_premium(message: Message):
    user_id = message.chat.id
    if user_id in admins:
        parts = message.text.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_user_id = int(parts[1])
            if target_user_id in users_data:
                users_data[target_user_id]["is_premium"] = True
                await message.answer(f"Премиум-доступ предоставлен пользователю {target_user_id}.")
            else:
                await message.answer("Пользователь не найден.")
        else:
            await message.answer("Используйте: /grant_premium <user_id>", parse_mode=None)
    else:
        await message.answer("У вас нет прав администратора.")


# Хендлер для команды /remove_user
@router.message(F.text.startswith("/remove_user"))
async def remove_user(message: Message):
    user_id = message.chat.id
    if user_id in admins:
        parts = message.text.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_user_id = int(parts[1])
            if target_user_id in users_data:
                del users_data[target_user_id]
                await message.answer(f"Пользователь {target_user_id} удалён.")
            else:
                await message.answer("Пользователь не найден.")
        else:
            await message.answer("Используйте: /remove_user <user_id>", parse_mode=None)
    else:
        await message.answer("У вас нет прав администратора.")