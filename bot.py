import asyncio
import random
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

async def monitor_links():
    driver = setup_driver()
    try:
        while True:
            for user_id, data in users_data.items():
                # Убедимся, что ключи 'sent_items' и 'previous_items' существуют
                if "sent_items" not in data:
                    data["sent_items"] = set()
                if "previous_items" not in data:
                    data["previous_items"] = set()

                if data["links"]:
                    for link in data["links"]:
                        # Получаем текущие товары с помощью fetch_vinted_items
                        items = await asyncio.to_thread(fetch_vinted_items, link, driver)
                        current_items = {item["item_id"] for item in items}  # Собираем все уникальные ID товаров

                        # Определяем новые элементы, которых не было в предыдущем наборе
                        new_items = current_items - data["previous_items"]

                        # Отправляем только те элементы, которые не были отправлены ранее
                        for item in items:
                            if item["item_id"] in new_items and item["item_id"] not in data["sent_items"]:
                                builder = InlineKeyboardBuilder()
                                builder.row(types.InlineKeyboardButton(
                                    text="Show", url=item["item_url"])
                                )
                                if item["title"]:  # Проверка наличия названия товара
                                    await bot.send_message(
                                        user_id,
                                        "\n".join(
                                            part.replace(":", ": <b>") + "</b>" if ":" in part else part for part in
                                            item["title"].split(", ")) + f"\n{hide_link(item['img_url'])}",
                                        reply_markup=builder.as_markup()
                                    )
                                    # Добавляем ID товара в список отправленных товаров
                                    data["sent_items"].add(item["item_id"])
                                    logger.info(f"Sent new item: {item['title']} to user {user_id}")
                                else:
                                    logger.warning(f"Item without title, skipping.")
                            else:
                                logger.debug(
                                    f"Item with ID {item['item_id']} already sent to user {user_id}, skipping.")

                        # Обновляем предыдущие элементы для следующей итерации после отправки всех новых элементов
                        data["previous_items"] = current_items

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
            EC.presence_of_all_elements_located((By.CLASS_NAME, "feed-grid"))
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы: {e}")
        return []

    items = driver.find_elements(By.CLASS_NAME, "u-position-relative")
    results = []

    for item in items:
        try:
            title_element = item.find_element(By.XPATH,
                                              "/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[15]/div/div[1]/div/div/div/div[2]/div[1]/div/img")  # Обновлённый путь для заголовка
            element_url = item.find_element(By.XPATH,
                                            "/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[15]/div/div[1]/div/div/div/div[2]/a")
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
    print(results)

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
