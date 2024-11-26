import asyncio
import random
import re
import time

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hide_link
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from aiogram.fsm.state import StatesGroup, State
from create_bot import logger, bot, dp, users_data
from handlers import main_commands, admin_commands


# Определяем состояния
class LinkStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_link_removal = State()
    waiting_for_admin_action = State()
    waiting_for_generated_link_name = State()


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


# Нормализация идентификатора, извлечение только числовой части
def normalize_item_id(item_id):
    match = re.search(r'\d+', item_id)
    return match.group(0) if match else item_id


async def monitor_links():
    driver = setup_driver()  # Настройка драйвера
    try:
        while True:
            for user_id, data in users_data.items():
                # Проверяем наличие ключей
                data.setdefault("sent_items", set())
                data.setdefault("previous_items", {})

                if data["links"]:
                    for link in data["links"]:
                        # Получаем текущие товары
                        items = await asyncio.to_thread(fetch_vinted_items, link, driver)
                        # Нормализуем текущие идентификаторы
                        current_items = {normalize_item_id(item["item_id"]): item for item in items}

                        # Логируем полученные текущие товары
                        logger.info(f"[{link}] Current items ({len(current_items)}): {list(current_items.keys())}")

                        # Пропускаем первую итерацию, инициализируя previous_items
                        if link not in data["previous_items"]:
                            data["previous_items"][link] = current_items
                            logger.info(f"[{link}] Initialized previous_items with {len(current_items)} items")
                            continue

                        # Логируем состояние previous_items перед сравнением
                        previous_items = data["previous_items"][link]
                        logger.info(f"[{link}] Previous items ({len(previous_items)}): {list(previous_items.keys())}")

                        # Находим новые товары
                        new_items = {
                            item_id: item
                            for item_id, item in current_items.items()
                            if item_id not in previous_items and item_id not in data["sent_items"]
                        }

                        # Логируем предварительные новые товары
                        logger.info(f"[{link}] Preliminary new items ({len(new_items)}): {list(new_items.keys())}")

                        # Исключаем "старые" товары, которые могли быть добавлены с предыдущей страницы
                        for item_id in previous_items.keys():
                            if item_id in current_items and current_items[item_id] == previous_items[item_id]:
                                new_items.pop(item_id, None)

                        # Логируем окончательные новые товары
                        logger.info(f"[{link}] Final new items ({len(new_items)}): {list(new_items.keys())}")

                        # Передаем найденные новые товары для отправки
                        if new_items:
                            await send_new_items(new_items, user_id, data)

                        # Обновляем предыдущие элементы
                        data["previous_items"][link] = current_items
                        logger.info(f"[{link}] Updated previous_items with {len(current_items)} items")

                # Логируем отправленные элементы для данного пользователя
                logger.info(f"[User {user_id}] Sent items ({len(data['sent_items'])}): {list(data['sent_items'])}")

            await asyncio.sleep(30)
    finally:
        driver.quit()


async def send_new_items(new_items, user_id, data):
    for item_id, item in new_items.items():
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Show", url=item["item_url"]))

        if item["title"]:
            await bot.send_message(
                user_id,
                f"<b>{item['title']}</b>\n{hide_link(item['img_url'])}",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            data["sent_items"].add(item_id)
            logger.info(f"Sent item {item['title']} to user {user_id}")


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
            EC.presence_of_all_elements_located((By.CLASS_NAME, "feed-grid"))
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы: {e}")
        return []

    items = driver.find_elements(By.CSS_SELECTOR, ".u-position-relative.u-min-height-none.u-flex-auto")[:10]

    results = []

    for item in items:
        try:
            title_element = item.find_element(By.TAG_NAME, "img")  # Обновлённый путь для заголовка
            element_url = item.find_element(By.TAG_NAME, "a")  # Собираем все данные об элементе

            # Собираем все данные об элементе
            item_data = {
                "title": title_element.get_attribute('alt'),
                "img_url": title_element.get_attribute('src'),
                "item_id": title_element.get_attribute('data-testid'),
                "item_url": element_url.get_attribute('href')
            }
            results.append(item_data)
        except Exception as e:
            logger.error(f"Ошибка обработки элемента: {e}")
    print(len(results))

    return results


# Запуск бота и мониторинга
async def main():
    logger.info("Bot started")
    dp.include_routers(main_commands.router, admin_commands.router)
    await asyncio.gather(
        bot.delete_webhook(drop_pending_updates=True),
        dp.start_polling(bot),
        monitor_links()
    )


if __name__ == "__main__":
    asyncio.run(main())
