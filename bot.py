import logging
import asyncio
import random
import time

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hide_link
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config_reader import config
from aiogram.client.default import DefaultBotProperties
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(
    token=config.bot_token.get_secret_value(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
dp = Dispatcher()

admins = {963960111}  # Замените на ID администраторов
# Хранилище пользователей и их ссылок
users_data = {}  # Структура: {user_id: {"links": [], "sent_items": set(), "is_premium": False, "is_admin": False}}

# Создание клавиатуры
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить ссылку")],
        [KeyboardButton(text="Удалить ссылку")],
        [KeyboardButton(text="Показать список")],
        [KeyboardButton(text="Помощь")],
        [KeyboardButton(text="Администрирование")]
    ],
    resize_keyboard=True
)


# Определяем состояния
class LinkStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_link_removal = State()
    waiting_for_admin_action = State()


# Хендлер для команды /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.chat.id
    if user_id not in users_data:
        # Инициализируем пользователя с ключом 'sent_items'
        users_data[user_id] = {"links": [], "sent_items": set(), "is_premium": False, "is_admin": user_id in admins}
    await message.answer(
        "Привет! Я бот для отслеживания товаров на Vinted.\n"
        "Выберите действие с помощью кнопок ниже:",
        reply_markup=keyboard
    )
    logger.info(f"User {user_id} started the bot")


# Хендлер для кнопки "Добавить ссылку"
@dp.message(F.text == "Добавить ссылку")
async def add_link_start(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте ссылку для отслеживания.")
    await state.set_state(LinkStates.waiting_for_link)


# Хендлер для получения ссылки от пользователя
@dp.message(LinkStates.waiting_for_link)
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
@dp.message(F.text == "Удалить ссылку")
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
@dp.message(LinkStates.waiting_for_link_removal)
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
@dp.message(F.text == "Показать список")
async def show_links(message: Message):
    user_id = message.chat.id
    if users_data[user_id]["links"]:
        links = "\n".join(users_data[user_id]["links"])
        await message.answer(f"Ваши отслеживаемые ссылки:\n{links}")
    else:
        await message.answer("У вас нет добавленных ссылок для отслеживания.")


# Хендлер для кнопки "Помощь"
@dp.message(F.text == "Помощь")
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


# Хендлер для кнопки "Администрирование"
@dp.message(F.text == "Администрирование")
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
@dp.message(F.text.startswith("/view_users"))
async def view_users(message: Message):
    user_id = message.chat.id
    if user_id in admins:
        user_list = "\n".join([f"User ID: {uid}, Premium: {data['is_premium']}" for uid, data in users_data.items()])
        await message.answer(f"Список всех пользователей:\n{user_list}")
    else:
        await message.answer("У вас нет прав администратора.")


# Хендлер для команды /grant_premium
@dp.message(F.text.startswith("/grant_premium"))
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
            await message.answer("Используйте: /grant_premium <user_id>")
    else:
        await message.answer("У вас нет прав администратора.")


# Хендлер для команды /remove_user
@dp.message(F.text.startswith("/remove_user"))
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
            await message.answer("Используйте: /remove_user <user_id>")
    else:
        await message.answer("У вас нет прав администратора.")


# Настройка Chrome в headless режиме
def setup_driver():
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Установка User-Agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Ошибка инициализации драйвера: {e}")
        raise


async def monitor_links():
    driver = setup_driver()
    try:
        while True:
            for user_id, data in users_data.items():
                # Убедимся, что ключ 'sent_items' существует
                if "sent_items" not in data:
                    data["sent_items"] = set()

                if data["links"]:
                    for link in data["links"]:
                        item_description, item_image_content, item_data_testid, item_url = await asyncio.to_thread(
                            fetch_vinted_items,
                            link, driver)
                        for title, img_url, item_id, item_url in zip(item_description, item_image_content,
                                                                     item_data_testid, item_url):
                            # Убедитесь, что товар имеет уникальный img_url и все его данные корректны
                            if img_url and img_url not in data["sent_items"]:
                                builder = InlineKeyboardBuilder()
                                builder.row(types.InlineKeyboardButton(
                                    text="Show", url=item_url)
                                )
                                if title:  # Проверка наличия названия товара
                                    await bot.send_message(
                                        user_id,
                                        f"{title}\n"
                                        f"{hide_link(img_url)}",
                                        reply_markup=builder.as_markup()
                                    )
                                    # Добавляем ссылку на изображение в список отправленных товаров
                                    data["sent_items"].add(img_url)
                                    logger.info(f"Sent new item: {title} to user {user_id}")
                                else:
                                    logger.warning(f"Item without title, skipping.")
                            else:
                                logger.info(f"Item with image {img_url} already sent to user {user_id}, skipping.")
            await asyncio.sleep(30)
    finally:
        driver.quit()


# Случайная задержка при обращении к сайту
def random_delay(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))


# Функция для получения и парсинга данных с сайта Vinted
def fetch_vinted_items(url, driver):
    logger.info(f"Fetching items from URL: {url}")
    try:
        random_delay()
        driver.get(url)
        logger.info("Page loaded, waiting for items to appear...")

        # Явное ожидание загрузки контента
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "new-item-box__container"))
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы: {e}")
        return [], [], []

    items = driver.find_elements(By.CLASS_NAME, "new-item-box__container")
    item_description, item_image_content, item_data_testid, item_url = [], [], [], []

    for item in items:
        try:
            title_element = item.find_element(By.XPATH,
                                              '/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[15]/div/div[1]/div/div/div/div[2]/a')
            item_description.append(title_element.get_attribute('title'))
            item_url.append(title_element.get_attribute('href'))
        except Exception as e:
            item_description.append(None)
            logger.error(f"Ошибка получения названия товара: {e}")

        try:
            img_element = item.find_element(By.XPATH,
                                            '/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[15]/div/div[1]/div/div/div/div[2]/div[1]/div/img')
            item_image_content.append(img_element.get_attribute('src'))
        except Exception as e:
            item_image_content.append(None)
            logger.error(f"Ошибка получения изображения товара: {e}")

        try:
            item_data_testid.append(item.get_attribute('data-testid'))
        except Exception as e:
            item_data_testid.append(None)
            logger.error(f"Ошибка получения ID товара: {e}")

    return item_description, item_image_content, item_data_testid, item_url


# Запуск бота и мониторинга
async def main():
    logger.info("Bot started")
    await asyncio.gather(
        dp.start_polling(bot),
        monitor_links()
    )


if __name__ == "__main__":
    asyncio.run(main())
