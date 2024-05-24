import telebot
import re
import yaml
import ast
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio
from PIL import Image, ImageFont, ImageDraw, ImageOps

from core import config, logging, messages, bot
from core.database import States, AsyncSessionLocal, Pet, db, get_data


async def generate_markup(buttons, buttons_in_row=2):
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

    return markup


# Отправка сообщения владельцу бота
async def owner_send(message):
    await bot.send_message(config["secret"]["owner_id"], message)


async def user_send(user_id, message, markup=None):
    if markup:
        await bot.send_message(user_id, message, reply_markup=markup)
    else:
        await bot.send_message(user_id, message)


async def remove_patterns(input_text):    
    patterns = [r' \(\S+\)$', r' \[\d+\]$']
    for pattern in patterns:
        input_text = re.sub(pattern, '', input_text)
    return input_text


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
            panel_img = Image.open(f"{config['imgs']['path_panels_folder']}/{data['panel_img']}", "r")

            background.paste(
                pet_img, (100, background.height - pet_img.height - 5), pet_img
            )

            font = ImageFont.truetype(
                f"{config['imgs']['font_path']}", config["imgs"]["font_size_info"]
            )
            draw = ImageDraw.Draw(panel_img)

            draw.text(
                (100, panel_img.height / 2),
                str(pet.health),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )
            draw.text(
                (220, panel_img.height / 2),
                str(pet.satiety),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )
            draw.text(
                (338, panel_img.height / 2),
                str(pet.happiness),
                (255, 255, 255),
                font=font,
                anchor="mm",
            )
            draw.text(
                (450, panel_img.height / 2),
                str(pet.sleep),
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
            background = Image.open(f"{config['imgs']['path_backgrounds_folder']}/{data['background_img']}", 'r')
            egg = Image.open(f"{config['imgs']['path_eggs_folder']}/{data['egg_img']}", 'r')
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
