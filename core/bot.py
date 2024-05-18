from core import bot, messages, logging
from core.utils import generate_markup, new_user


@bot.message_handler(commands=["start"])
async def start_handler(message):
    logging.info(f"{message.from_user.id} - Отправка приветственного сообщения")
    markup = await generate_markup(messages["bot"]["start"]["buttons"])
    status, text = await new_user(message)
    if status:
        await bot.send_message(
            message.chat.id, messages["bot"]["start"]["text"], reply_markup=markup
        )

    else:
        await bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["help"])
async def help_handler(message):
    logging.warning(f"{message.from_user.id} - Использование /help")
    await bot.send_message(message.chat.id, messages["bot"]["help"]["text"])


@bot.message_handler(commands=["debug"])
async def debug(message):
    logging.warning(f"{message.from_user.id} - Использование /debug")
    with open("logs/latest.log", "rb") as f:
        await bot.send_document(message.chat.id, f)


