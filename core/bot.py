from core import bot, messages, logging
from core.interface import check_triggers, show_interface, parse_food, parse_games
from core.utils import (
    generate_markup,
    remove_patterns,
    get_current_page,
    update_current_page,
    get_total_items,
    get_current_category,
    get_message_for_delete,
    set_message_for_delete,
    escape_text,
)
from core.database import set_state, AsyncSessionLocal, States, db

import time


@bot.message_handler(commands=["debug"])
async def debug(message):
    logging.warning(f"{message.from_user.id} - Использование /debug")
    with open("logs/latest.log", "rb") as f:
        await bot.send_document(message.chat.id, f)


@bot.message_handler()
async def main_handler(message):
    user_id = message.chat.id
    if message.text == messages["buttons"]["back_page"]:
        await bot.delete_message(message.chat.id, message.id)
        message_for_delete = await get_message_for_delete(message.from_user.id)
        if message_for_delete:
            try:
                await bot.delete_message(message.chat.id, message_for_delete)
            except:
                pass

        category = await get_current_category(user_id)
        current_page = await get_current_page(user_id)

        if current_page > 1:
            new_page = current_page - 1
            await update_current_page(user_id, new_page)
            if category == "food":
                markup = await parse_food(user_id)
            elif category == "games":
                markup = await parse_games(user_id)

            update = await bot.send_message(
                user_id,
                messages["buttons"]["update_page"],
                reply_markup=markup,
                parse_mode="HTML",
            )
            await set_message_for_delete(user_id, update.id)
    elif message.text == messages["buttons"]["next_page"]:
        await bot.delete_message(message.chat.id, message.id)
        message_for_delete = await get_message_for_delete(message.from_user.id)
        if message_for_delete:
            try:
                await bot.delete_message(message.chat.id, message_for_delete)
            except:
                pass

        category = await get_current_category(user_id)
        current_page = await get_current_page(user_id)
        total_items = await get_total_items(user_id, category)
        total_pages = (
            total_items + messages["buttons"]["items_per_page"] - 1
        ) // messages["buttons"]["items_per_page"]

        if current_page < total_pages:
            new_page = current_page + 1
            await update_current_page(user_id, new_page)

        if category == "food":
            markup = await parse_food(user_id)
        elif category == "games":
            markup = await parse_games(user_id)

        update = await bot.send_message(
            user_id,
            messages["buttons"]["update_page"],
            reply_markup=markup,
            parse_mode="HTML",
        )
        await set_message_for_delete(user_id, update.id)

    else:
        start_check = time.time()
        status, input, interface_name = await check_triggers(
            message.from_user.id, message.text
        )
        finish = time.time()
        res = finish - start_check
        res_msec = res * 1000
        print('Время работы check_triggers в миллисекундах: ', res_msec)

        
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
                start_interface = time.time()
                await set_state(message.from_user.id, interface_name)
                text, img, markup = await show_interface(
                    message.from_user.id, interface_name
                )
                finish = time.time()
                res = finish - start_interface
                res_msec = res * 1000
                print('Время работы show_interface в миллисекундах: ', res_msec)
                

            # text = await escape_text(text)
            start_send = time.time()
            if img != "None":
                if markup != "None":
                    await bot.send_photo(
                        message.chat.id,
                        photo=img,
                        caption=text,
                        reply_markup=markup,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_photo(
                        message.chat.id,
                        photo=img,
                        caption=text,
                        parse_mode="HTML"
                    )
            else:
                if markup != "None":
                    await bot.send_message(
                        message.chat.id, text, reply_markup=markup, parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        message.chat.id, text, parse_mode="HTML"
                    )

        else:
            await bot.send_message(message.chat.id, interface_name, parse_mode="HTML")
            
        finish = time.time()
        res = finish - start_send
        res_msec = res * 1000
        print('Время работы send в миллисекундах: ', res_msec)