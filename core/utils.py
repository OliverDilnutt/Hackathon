import telebot
import re
import yaml
import ast
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio

from core import data, logging, messages, bot
from core.database import User, Session


async def generate_markup(buttons):
    markup = telebot.async_telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons:
        markup.add(button)

    return markup


# Отправка сообщения владельцу бота
async def owner_send(message):
    await bot.send_message(data["secret"]["owner_id"], message)


async def new_user(message):
    session = Session()
    user = session.query(User).filter(User.user_id == message.from_user.id).first()
    if not user:
        user = User(user_id=message.from_user.id)
        session.add(user)
        session.commit()
        session.close()
        return True, ""
    else:
        return False, messages['bot']['start']['already_reg']