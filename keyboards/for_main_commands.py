from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder




keyboard = ReplyKeyboardBuilder()
keyboard.add(KeyboardButton(text="Добавить ссылку"))
keyboard.add(KeyboardButton(text="Сгенерировать ссылку"))
keyboard.add(KeyboardButton(text="Удалить ссылку"))
keyboard.add(KeyboardButton(text="Показать список"))
keyboard.add(KeyboardButton(text="Помощь"))
keyboard.adjust(2)