from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, KeyboardButton
from bot import LinkStates
from create_bot import admins, users_data
from keyboards.for_main_commands import keyboard
from bot import logger

router = Router()


# Хендлер для команды /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.chat.id
    if user_id not in users_data:
        # Инициализируем пользователя с ключом 'sent_items'
        users_data[user_id] = {"links": [], "sent_items": set(), "is_premium": False, "is_admin": user_id in admins}
        if users_data[user_id]["is_admin"]:
            users_data[user_id]["is_premium"] = True
            keyboard.add(KeyboardButton(text="Администрирование"))
    await message.answer(
        "Привет! Я бот для отслеживания товаров на Vinted.\n"
        "Выберите действие с помощью кнопок ниже:",
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )
    logger.info(f"User {user_id} started the bot")


# Хендлер для кнопки "Добавить ссылку"
@router.message(F.text == "Добавить ссылку")
async def add_link_start(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте ссылку для отслеживания.")
    await state.set_state(LinkStates.waiting_for_link)


# Хендлер для получения ссылки от пользователя
@router.message(LinkStates.waiting_for_link)
async def save_link(message: Message, state: FSMContext):
    user_id = message.chat.id
    link = message.text
    if link.startswith("https://www.vinted."):
        users_data[user_id]["links"].append(link)
        await message.answer(f"Ссылка {link} добавлена для отслеживания.")
        logger.info(f"Link {link} added by user {user_id}")
    else:
        await message.answer("Пожалуйста, отправьте правильную ссылку, начинающуюся с 'https://www.vinted.'.")
    await state.clear()


# Хендлер для кнопки "Удалить ссылку"
@router.message(F.text == "Удалить ссылку")
async def remove_link_start(message: Message, state: FSMContext):
    user_id = message.chat.id
    if users_data[user_id]["links"]:
        links = "\n".join(users_data[user_id]["links"])
        await message.answer(
            f"Ваши отслеживаемые ссылки:\n{links}\nПожалуйста, отправьте ссылку, которую хотите удалить.")
        await state.set_state(LinkStates.waiting_for_link_removal)
    else:
        await message.answer("У вас нет добавленных ссылок для отслеживания.")


# Хендлер для удаления ссылки
@router.message(LinkStates.waiting_for_link_removal)
async def remove_link(message: Message, state: FSMContext):
    user_id = message.chat.id
    link = message.text
    if link in users_data[user_id]["links"]:
        users_data[user_id]["links"].remove(link)
        await message.answer(f"Ссылка {link} удалена из отслеживания.")
        logger.info(f"Link {link} removed by user {user_id}")
    else:
        await message.answer("Эта ссылка не найдена в вашем списке.")
    await state.clear()


# Хендлер для кнопки "Показать список"
@router.message(F.text == "Показать список")
async def show_links(message: Message):
    user_id = message.chat.id
    if users_data[user_id]["links"]:
        links = "\n".join(users_data[user_id]["links"])
        await message.answer(f"Ваши отслеживаемые ссылки:\n{links}")
    else:
        await message.answer("У вас нет добавленных ссылок для отслеживания.")


# Хендлер для кнопки "Помощь"
@router.message(F.text == "Помощь")
async def show_help(message: Message):
    help_text = (
        "Этот бот помогает отслеживать товары на сайте Vinted.\n\n"
        "Вот доступные команды:\n"
        "/start - Запустить бота\n"
        "Добавить ссылку - Отправить ссылку, которую бот будет отслеживать\n"
        "Удалить ссылку - Удалить ссылку из отслеживания\n"
        "Показать список - Показать все добавленные ссылки для отслеживания\n"
        "Помощь - Информация о боте"
    )
    await message.answer(help_text)
