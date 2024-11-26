import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config_reader import config

admins = {int(admin_id) for admin_id in config.admins.get_secret_value().split(',')}

users_data = {}  # Структура: {user_id: {"links": [], "sent_items": set(), "is_premium": False, "is_admin": False, "is_banned": False}}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=config.bot_token.get_secret_value(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))

dp = Dispatcher()
