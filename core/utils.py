import telebot
import re
import textwrap
from sqlalchemy import func
from datetime import datetime, timedelta
import random
from PIL import Image, ImageFont, ImageDraw, ImageOps
import os
from math import floor

from core import config, logging, messages, bot
from core.database import States, AsyncSessionLocal, Pet, db, get_data, get_inventory


async def escape_text(text):
    def replace(match):
        text = match.group(0)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    # Regular expression to match text outside of HTML tags
    pattern = re.compile(r"(?s)(?:(<[^>]*>)|([^<]*))")
    return pattern.sub(
        lambda match: match.group(1) if match.group(1) else replace(match), text
    )


async def generate_markup(
    buttons, buttons_in_row=2, special_buttons=None, special_buttons_in_row=None
):
    markup = telebot.async_telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for button in buttons:
        if button != "None":
            row.append(button)
            if len(row) == buttons_in_row:
                markup.row(*row)
                row = []
    if row:
        markup.row(*row)

    if special_buttons:
        row = []
        for button in special_buttons:
            if button != "None":
                row.append(button)
                if len(row) == special_buttons_in_row:
                    markup.row(*row)
                    row = []
        if row:
            markup.row(*row)

    return markup


# Отправка сообщения владельцу бота
async def owner_send(message):
    await bot.send_message(config["secret"]["owner_id"], message)


async def user_send(user_id, message, markup=None):
    message = await escape_text(message)
    if markup:
        try:
            await bot.send_message(user_id, message, reply_markup=markup, parse_mode="HTML")
        except:
            pass
    else:
        try:
            await bot.send_message(user_id, message, parse_mode="HTML")
        except:
            pass


async def remove_patterns(input_text):
    patterns = [
        r" \(\S+\)$",
        r" \[\d+\]$",
    ]
    for pattern in patterns:
        input_text = re.sub(pattern, "", input_text)
    return input_text


async def get_current_page(user_id):
    async with AsyncSessionLocal() as session:
        state = await session.execute(
            db.select(States).filter(States.user_id == user_id)
        )
        state = state.scalar_one_or_none()
        if state:
            return state.current_page


async def update_current_page(user_id, new_page):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            state = await session.execute(
                db.select(States).filter(States.user_id == user_id)
            )
            state = state.scalar_one_or_none()
            if state:
                state.current_page = new_page
            await session.commit()


async def generate_paginated_markup(items, page, items_per_page, buttons_in_row):
    total_items = len(items)
    total_pages = (total_items + items_per_page - 1) // items_per_page

    start = (page - 1) * items_per_page
    end = start + items_per_page
    items_page = items[start:end]

    actions = []
    if page > 1:
        actions.insert(0, messages["buttons"]["back_page"])
    actions.append(messages["buttons"]["actions"])
    if page < total_pages:
        actions.append(messages["buttons"]["next_page"])
    if buttons_in_row is not None:
        markup = await generate_markup(
            items_page,
            buttons_in_row=buttons_in_row,
            special_buttons=actions,
            special_buttons_in_row=3,
        )
    else:
        markup = await generate_markup(
            items_page,
            buttons_in_row=2,
            special_buttons=actions,
            special_buttons_in_row=3,
        )
    return markup


async def set_message_for_delete(user_id, message_id):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            state = await session.execute(
                db.select(States).filter(States.user_id == user_id)
            )
            state = state.scalar_one_or_none()
            if state:
                state.msg_for_delete = message_id
            await session.commit()


async def get_message_for_delete(user_id):
    async with AsyncSessionLocal() as session:
        state = await session.execute(
            db.select(States).filter(States.user_id == user_id)
        )
        state = state.scalar_one_or_none()
        if state:
            return state.msg_for_delete
        return None


async def get_total_items(user_id, category):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        if category == "food":
            inventory = await get_inventory(pet.id)
            total_items = sum(
                1 for item in inventory.values() if item["class"] == category
            )
        elif category == "games":
            games = config["games"]["list"]
            total_items = len(games)
        return total_items
    return 0


async def update_current_category(user_id, category):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            states = await session.execute(
                db.select(States).filter(States.user_id == user_id)
            )
            state = states.scalar_one_or_none()
            if state:
                state.current_category = category
            await session.commit()


async def get_current_category(user_id):
    async with AsyncSessionLocal() as session:
        states = await session.execute(
            db.select(States).filter(States.user_id == user_id)
        )
        state = states.scalar_one_or_none()
        if state:
            return state.current_category
        return None


async def save_time_start_activity(pet_id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            pet = await session.execute(db.select(Pet).filter(Pet.id == pet_id))
            pet = pet.scalar_one_or_none()
            if pet:
                data = await get_data(pet_id)
                data["time_start_activity"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
                pet.data = str(data)
            await session.commit()


async def get_player_rank(user_id, sorted_pets):
    for idx, pet in enumerate(sorted_pets, start=1):
        if pet.user_id == user_id:
            return idx


async def split_text(text, max_length):
    paragraphs = text.split("\n")
    split_paragraphs = []

    for paragraph in paragraphs:
        if len(paragraph) <= max_length:
            split_paragraphs.append(paragraph)
        else:
            wrapped_lines = textwrap.wrap(
                paragraph, width=max_length, replace_whitespace=False
            )
            split_paragraphs.extend(wrapped_lines)

    return split_paragraphs


async def get_index_state(index, parameter):
    states_dict = messages.get("indexes_states", {}).get(parameter, {})
    index = int(index)  # Преобразуем индекс к целому числу
    for interval, state_list in states_dict.items():
        interval_start, interval_end = map(int, interval.strip("[]").split(", "))
        if interval_start <= index <= interval_end:
            return random.choice(state_list)


async def create_info_image(user_id):
    async with AsyncSessionLocal() as session:
        pet = await session.execute(
            db.select(Pet).filter(Pet.user_id == user_id and Pet.status == "live")
        )
        pet = pet.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            background = Image.open(
                f"{config['imgs']['path_rooms_folder']}/{data['room_img']}", "r"
            )
            pet_img = Image.open(
                f"{config['imgs']['path_pets_folder']}/{data['pet_img']}", "r"
            )
            panel_img = Image.open(
                f"{config['imgs']['path_panels_folder']}/{data['panel_img']}", "r"
            )

            background.paste(
                pet_img, (100, background.height - pet_img.height - 5), pet_img
            )

            font = ImageFont.truetype(
                f"{config['imgs']['font_path']}", config["imgs"]["font_size_info"]
            )
            draw = ImageDraw.Draw(panel_img)

            draw.text(
                (100, panel_img.height / 2),
                str(round(pet.health, 1)),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )
            draw.text(
                (220, panel_img.height / 2),
                str(round(pet.satiety, 1)),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )
            draw.text(
                (338, panel_img.height / 2),
                str(round(pet.happiness, 1)),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )
            draw.text(
                (450, panel_img.height / 2),
                str(round(pet.sleep, 1)),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )

            background.paste(
                panel_img,
                (
                    background.width - panel_img.width - 15,
                    background.height - panel_img.height - 15,
                ),
                panel_img,
            )

            return True, background
        else:
            return False, messages["errors"]["not_have_pet"]


async def egg_show(user_id):
    from core.interface import hatching_check_interface

    async with AsyncSessionLocal() as session:
        pet = await session.execute(
            db.select(Pet).filter(Pet.user_id == user_id and Pet.status == "live")
        )
        pet = pet.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            background = Image.open(
                f"{config['imgs']['path_backgrounds_folder']}/{data['background_img']}",
                "r",
            )
            egg = Image.open(
                f"{config['imgs']['path_eggs_folder']}/{data['egg_img']}", "r"
            )
            egg = ImageOps.scale(egg, 0.5, resample=Image.LANCZOS)
            markup_egg = (0, 50)
            background.paste(egg, markup_egg, egg)

            font = ImageFont.truetype(
                f"{config['imgs']['font_path']}", config["imgs"]["font_size_eggs"]
            )

            status, text = await hatching_check_interface(pet.user_id, True)

            if status:
                draw = ImageDraw.Draw(background)
                draw.text(
                    (700, 200),
                    text,
                    (255, 255, 255),
                    font=font,
                    anchor="mm",
                )

            return True, background
        else:
            return False, None


async def journey_images(user_id):
    async with AsyncSessionLocal() as session:
        pet = await session.execute(
            db.select(Pet).filter(Pet.user_id == user_id and Pet.status == "live")
        )
        pet = pet.scalar_one_or_none()
        if pet:
            if pet.state == 'traveling':
                data = await get_data(pet.id)
                background_files = os.listdir(
                    messages["events"]["journey"][data["journey_location"]]["img"]
                )
                background_file = background_files[
                    random.randint(0, len(background_files) - 1)
                ]
                background_path = os.path.join(
                    messages["events"]["journey"][data["journey_location"]]["img"],
                    background_file,
                )
                background = Image.open(background_path, "r")
                return True, background
            else:
                return False, None

        else:
            return False, None
