import telebot
import re
import yaml
import ast
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio
from PIL import Image, ImageFont, ImageDraw

from core import config, logging, messages, bot
from core.database import States, AsyncSessionLocal, Pet, db, get_data


async def generate_markup(buttons):
    markup = telebot.async_telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for button in buttons:
        if button != 'None':
            row.append(button)
            if len(row) == 2:
                markup.row(*row)
                row = []

    if row:
        markup.row(*row)

    return markup


# Отправка сообщения владельцу бота
async def owner_send(message):
    await bot.send_message(config["secret"]["owner_id"], message)


async def user_send(user_id, message):
    await bot.send_message(user_id, message)
    
    
async def create_info_image(user_id):
    async with AsyncSessionLocal() as session:
        pet = await session.execute(db.select(Pet).filter(Pet.user_id == user_id and Pet.status == "live"))
        pet = pet.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            background = Image.open(f"{config['imgs']['path_rooms_folder']}/{data['room_img']}", 'r')
            pet_img = Image.open(f"{config['imgs']['path_pets_folder']}/{data['pet_img']}", 'r')
            panel_img = Image.open("imgs/panels/panel_1.png", 'r')
            
            background.paste(pet_img, (100, background.height - pet_img.height - 34), pet_img)
            
            font = ImageFont.truetype(f"{config['imgs']['font_path']}", config['imgs']['font_size'])
            draw = ImageDraw.Draw(panel_img)
            
            draw.text((100, panel_img.height/2), str(pet.health), (255, 255, 255), font=font, anchor="mm")
            draw.text((220, panel_img.height/2), str(pet.satiety), (255, 255, 255), font=font, anchor="mm")
            draw.text((338, panel_img.height/2), str(pet.happiness), (255, 255, 255), font=font, anchor="mm")
            draw.text((450, panel_img.height/2), str(pet.sleep), (255, 255, 255), font=font, anchor="mm")
            
            background.paste(panel_img, (background.width - panel_img.width - 15, background.height - panel_img.height - 15), panel_img)
            
            return True, background
            