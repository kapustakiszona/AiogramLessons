import random
import time
import urllib
from urllib import parse

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
    logger.info(f"User {user_id} requested to remove a link.")
    if users_data.get(user_id) and users_data[user_id]["links"]:
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
    logger.info(f"User {user_id} wants to remove link: {link}")
    if link in users_data.get(user_id, {}).get("links", []):
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
        "Сгенерировать ссылку - Сгенерировать ссылку и добавить ее в отслеживаемые\n"
        "Удалить ссылку - Удалить ссылку из отслеживания\n"
        "Показать список - Показать все добавленные ссылки для отслеживания\n"
        "Помощь - Информация о боте"
    )
    await message.answer(help_text)

# Хендлер для кнопки "Сгенерировать ссылку"
@router.message(F.text == "Сгенерировать ссылку")
async def generate_link_start(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте название предмета для генерации ссылки.")
    await state.set_state(LinkStates.waiting_for_generated_link_name)

# Хендлер для получения названия предмета от пользователя
@router.message(LinkStates.waiting_for_generated_link_name)
async def generate_link(message: Message, state: FSMContext):
    user_id = message.chat.id
    item_name = message.text
    base_url = "https://www.vinted.pl/catalog"
    search_text = urllib.parse.quote(item_name)
    search_id = random.randint(1000000000, 9999999999)
    order = "newest_first"
    time_param = int(time.time())
    generated_link = f"{base_url}?search_text={search_text}&search_id={search_id}&order={order}&time={time_param}"

    users_data[user_id]["links"].append(generated_link)
    await message.answer(f"Ссылка для предмета '{item_name}' сгенерирована и добавлена для отслеживания: {generated_link}")
    logger.info(f"Generated link {generated_link} added by user {user_id}")
    await state.clear()