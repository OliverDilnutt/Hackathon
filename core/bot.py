from core import bot, messages, logging
from core.interface import check_triggers, show_interface
from core.utils import generate_markup
from core.database import set_state, Session, States


# @bot.message_handler(commands=["start"])
# async def start_handler(message):
#     markup = await generate_markup(messages["bot"]["start"]["buttons"])
#     # status, text = await new_user(message)
#     # if status:
#     await bot.send_message(message.chat.id, messages["bot"]["start"]["text"], reply_markup=markup)

#     # else:
#         # await bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["help"])
async def help_handler(message):
    logging.warning(f"{message.from_user.id} - Использование /help")
    await bot.send_message(message.chat.id, messages["bot"]["help"]["text"])


@bot.message_handler(commands=["debug"])
async def debug(message):
    logging.warning(f"{message.from_user.id} - Использование /debug")
    with open("logs/latest.log", "rb") as f:
        await bot.send_document(message.chat.id, f)


@bot.message_handler()
async def main_handler(message):
    status, input, interface_name = await check_triggers(
        message.from_user.id, message.text
    )
    if status:
        if input:
            session = Session()
            interface_name = session.query(States).filter(States.user_id == message.from_user.id).first().state
            session.close()
            interface_name = messages['interfaces'][interface_name].get('next_state')
            await set_state(message.from_user.id, interface_name)
            name, text, img, markup = await show_interface(
                message.from_user.id, interface_name, input
            )
        else:
            await set_state(message.from_user.id, interface_name)
            name, text, img, markup = await show_interface(
                message.from_user.id, interface_name
            )
        text = f"{name}\n\n{text}"
        if img != "None":
            await bot.send_photo(
                message.chat.id, photo=img, caption=text, reply_markup=markup
            )
        else:
            await bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        await bot.send_message(message.chat.id, interface_name)
