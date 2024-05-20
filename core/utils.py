import telebot
import re
import yaml
import ast
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio

from core import config, logging, messages, bot
from core.database import States, Session


async def generate_markup(buttons):
    markup = telebot.async_telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons:
        if button != 'None':
            markup.add(button)

    return markup


# Отправка сообщения владельцу бота
async def owner_send(message):
    await bot.send_message(config["secret"]["owner_id"], message)
