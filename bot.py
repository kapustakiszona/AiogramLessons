import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
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

# Хранилище для ссылок и последних предметов
tracking_links = {}
last_item_ids = {}
users_chat_ids = set()

# Создание клавиатуры
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить ссылку")],
        [KeyboardButton(text="Удалить ссылку")],
        [KeyboardButton(text="Показать список")],
        [KeyboardButton(text="Помощь")]
    ],
    resize_keyboard=True
)


# Определяем состояния
class LinkStates(StatesGroup):
    waiting_for_link = State()


# Хендлер для кнопки "Добавить ссылку"
@dp.message(F.text == "Добавить ссылку")
async def add_link_start(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте ссылку для отслеживания.")
    await state.set_state(LinkStates.waiting_for_link)


# Хендлер для получения ссылки от пользователя
@dp.message(LinkStates.waiting_for_link)
async def save_link(message: Message, state: FSMContext):
    link = message.text
    if link.startswith("https://www.vinted."):
        tracking_links[link] = []  # Добавляем ссылку в tracking_links
        await message.answer(f"Ссылка {link} добавлена для отслеживания.")
        logger.info(f"Link {link} added by user {message.chat.id}")
    else:
        await message.answer("Пожалуйста, отправьте правильную ссылку, начинающуюся с 'https://www.vinted.'.")

    await state.clear()  # Очищаем состояние


# Хендлер для кнопки "Удалить ссылку"
@dp.message(F.text == "Удалить ссылку")
async def remove_link_start(message: Message, state: FSMContext):
    if tracking_links:
        links = "\n".join(tracking_links.keys())
        await message.answer(f"Отслеживаемые ссылки:\n{links}\nПожалуйста, отправьте ссылку, которую хотите удалить.")
        await state.set_state(LinkStates.waiting_for_link)
    else:
        await message.answer("У вас нет добавленных ссылок для отслеживания.")
# Настройка Chrome в нормальном режиме (НЕ headless)
def setup_driver():
    try:
        chrome_options = Options()
        # Отключаем headless режим для тестирования
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Устанавливаем драйвер
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logger.info("Driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize the Chrome driver: {e}")
        raise


# Функция для получения и парсинга данных с сайта Vinted
def fetch_vinted_items(url, driver):
    logger.info(f"Fetching items from URL: {url}")
    try:
        driver.get(url)
        logger.info("Page loaded, waiting for items to appear...")

        # Явное ожидание загрузки контента
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "new-item-box__container"))
        )
        logger.info("Items are present on the page")
    except Exception as e:
        logger.error(f"Timeout or error loading the page: {e}")
        return [], [], []

    # Парсим данные о товарах
    items = driver.find_elements(By.CLASS_NAME, "new-item-box__container")
    logger.info(f"Found {len(items)} items on the page")

    item_titles, item_image_content, item_data_testid = [], [], []

    for index, item in enumerate(items):
        logger.info(f"Processing item {index + 1}/{len(items)}")
        try:
            title_element = item.find_element(By.XPATH,
                                              '/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[15]/div/div[1]/div/div/div/div[2]/a')
            item_titles.append(title_element.get_attribute('title'))
            logger.info(f"Title: {item_titles[-1]}")
        except Exception as e:
            item_titles.append(None)
            logger.error(f"Error getting title for item {index + 1}: {e}")

        try:
            img_element = item.find_element(By.XPATH,
                                            '/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[15]/div/div[1]/div/div/div/div[2]/div[1]/div/img')
            item_image_content.append(img_element.get_attribute('src'))
            logger.info(f"Image URL: {item_image_content[-1]}")
        except Exception as e:
            item_image_content.append(None)
            logger.error(f"Error getting image for item {index + 1}: {e}")

        try:
            item_data_testid.append(item.get_attribute('data-testid'))
            logger.info(f"Item ID: {item_data_testid[-1]}")
        except Exception as e:
            item_data_testid.append(None)
            logger.error(f"Error getting data-testid for item {index + 1}: {e}")

    return item_titles, item_image_content, item_data_testid


# Хендлер для команды /start (уже добавлен)
@dp.message(CommandStart())
async def cmd_start(message: Message):
    users_chat_ids.add(message.chat.id)
    logger.info(f"User {message.chat.id} started the bot")
    await message.answer(
        "Привет! Я бот для отслеживания товаров на Vinted.\n"
        "Выберите действие с помощью кнопок ниже:",
        reply_markup=keyboard
    )

# Хендлер для кнопки "Добавить ссылку"
@dp.message(F.text == "Добавить ссылку")
async def add_link(message: Message):
    await message.answer("Пожалуйста, отправьте ссылку для отслеживания.")
    logger.info(f"User {message.chat.id} requested to add a link")

# Хендлер для кнопки "Удалить ссылку"
@dp.message(F.text == "Удалить ссылку")
async def remove_link(message: Message):
    await message.answer("Пожалуйста, отправьте ссылку, которую хотите удалить.")
    logger.info(f"User {message.chat.id} requested to remove a link")

# Хендлер для кнопки "Показать список"
@dp.message(F.text == "Показать список")
async def show_links(message: Message):
    if tracking_links:
        links = "\n".join(tracking_links.keys())
        await message.answer(f"Отслеживаемые ссылки:\n{links}")
        logger.info(f"User {message.chat.id} requested the list of links")
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

# Хендлеры для команд

# Хранилище для отправленных ссылок на изображения
sent_image_urls = set()

# Функция для мониторинга и отправки новых товаров
async def monitor_links():
    logger.info("Initializing Chrome driver...")
    driver = setup_driver()  # Теперь драйвер должен инициализироваться
    logger.info("Chrome driver initialized and monitoring started")

    try:
        while True:
            logger.info("Starting a new monitoring cycle...")
            for link, last_ids in tracking_links.items():
                logger.info(f"Checking link: {link} with last known IDs: {last_ids}")

                # Получаем все три значения из fetch_vinted_items
                item_titles, item_image_content, item_data_testid = await asyncio.to_thread(fetch_vinted_items, link,
                                                                                            driver)

                if item_titles:  # Если есть новые товары
                    for title, img_url, item_id in zip(item_titles, item_image_content, item_data_testid):
                        logger.info(f"Checking item {title} with image URL {img_url}")
                        # Проверяем, был ли уже этот товар отправлен
                        if img_url not in sent_image_urls:
                            logger.info(f"Sending new item {title} to users.")
                            for chat_id in users_chat_ids:
                                try:
                                    await bot.send_message(
                                        chat_id=chat_id,
                                        text=f"Новый товар: {title}\nИзображение: {img_url}"
                                    )
                                    logger.info(f"New item {title} sent to chat ID: {chat_id}")
                                except Exception as e:
                                    logger.error(f"Error sending message to chat ID {chat_id}: {e}")

                            # Добавляем URL изображения в список отправленных
                            sent_image_urls.add(img_url)
                        else:
                            logger.info(f"Item {title} with image URL {img_url} has already been sent, skipping.")
                # Обновляем последние ID товаров
                tracking_links[link] = last_ids
            logger.info("Monitoring cycle complete. Sleeping for 30 seconds...")
            await asyncio.sleep(30)
    finally:
        driver.quit()
        logger.info("Driver quit and monitoring stopped.")




# Запуск бота и мониторинга
async def main():
    logger.info("Bot started")
    await asyncio.gather(
        dp.start_polling(bot),
        monitor_links()
    )


if __name__ == "__main__":
    asyncio.run(main())
