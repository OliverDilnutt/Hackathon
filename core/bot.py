import re

from core import bot, messages, logging
from core.interface import check_triggers, show_interface
from core.utils import generate_markup, remove_patterns
from core.database import set_state, AsyncSessionLocal, States, db
from core.engine import break_collect_food


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
            async with AsyncSessionLocal() as session:
                interface_name = await session.execute(
                    db.select(States).filter(States.user_id == message.from_user.id)
                )
                interface_name = interface_name.scalar_one_or_none().state
                interface_name = messages["interfaces"][interface_name].get(
                    "next_state"
                )
                await set_state(message.from_user.id, interface_name)

                input = await remove_patterns(input)
                    
                text, img, markup = await show_interface(
                    message.from_user.id, interface_name, input
                )
        else:
            await set_state(message.from_user.id, interface_name)
            text, img, markup = await show_interface(
                message.from_user.id, interface_name
            )

        if img != "None":
            await bot.send_photo(
                message.chat.id, photo=img, caption=text, reply_markup=markup
            )
        else:
            await bot.send_message(message.chat.id, text, reply_markup=markup)

    else:
        await bot.send_message(message.chat.id, interface_name)
