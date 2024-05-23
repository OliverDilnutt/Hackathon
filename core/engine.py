from core import config, logging, messages, bot, config_path
from core.database import Pet, AsyncSessionLocal, get_data, db
from core.utils import user_send

from datetime import datetime, timedelta
import asyncio
import yaml
import names
import os
import random


async def new_pet(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if not pet:
            pet = Pet(user_id=user_id)
            session.add(pet)
            
            files_pets = os.listdir(config['imgs']['path_pets_folder'])
            files_rooms = os.listdir(config['imgs']['path_rooms_folder'])
            
            random_pet = files_pets[random.randint(0, len(files_pets) - 1)]
            random_room = files_rooms[random.randint(0, len(files_rooms) - 1)]
            data = await get_data(pet.id)
            data['pet_img'] = random_pet
            data['room_img'] = random_room
            pet.data = str(data)
            await session.commit()
            return True, ""
        return False, messages["errors"]["already_have_pet"]


async def save_pet_name(user_id, input):
    pet_name = input
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            pet.name = pet_name
            await session.commit()
            return True, ""
        return False, messages["errors"]["not_have_pet"]


async def save_random_pet_name(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            name = names.get_first_name()
            pet.name = name
            await session.commit()
            text = messages['interfaces']["random_pet_name"]["text"]
            text = text.format(name)
            return True, text
        return False, messages["errors"]["not_have_pet"]


async def hunger(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet:
            if auto:
                pet.satiety = max(pet.satiety - config["food"]["hunger_index"], 0)
            else:
                pet.satiety = max(pet.satiety - index, 0)
            await session.commit()


async def sadness(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state != 'playing':
            if auto:
                pet.happiness = max(pet.happiness - config["engine"]["sadness_index"], 0)
            else:
                pet.happiness = max(pet.happiness - index, 0)
            await session.commit()


async def sleep_down(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state != 'sleeping':
            if auto:
                pet.sleep = max(pet.sleep - config["sleep"]["sleep_down_index"], 0)
            else:
                pet.sleep = max(pet.sleep - index, 0)
            await session.commit()


async def health(id, index=None, auto=True):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet:
            if auto:
                pet.health = max(pet.health - config["engine"]["health_index"], 0)
            else:
                pet.health = max(pet.health - index, 0)
            await session.commit()


async def get_age(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()
        if pet:
            born = datetime.strptime(pet.born, "%Y-%m-%d %H:%M:%S.%f")
            if pet.status == "live":
                age = datetime.now() - born
            else:
                death = datetime.strptime(pet.death, "%Y-%m-%d %H:%M:%S.%f")
                age = death - born
            if age.days > 0:
                return age.days, "days"
            elif age.seconds // 3600 > 0:
                return age.seconds // 3600, "hours"
            elif age.seconds // 60 > 0:
                return age.seconds // 60, "minutes"
            else:
                return age.seconds, "seconds"


async def die(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet:
            pet.status = "dead"
            pet.death = datetime.now()
            await session.commit()


async def get_info(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet:
            status = messages["statuses"]["live"] if pet.status == "live" else messages["statuses"]["dead"]
            data = {
                "id": pet.id,
                "name": pet.name,
                "satiety": pet.satiety,
                "happiness": pet.happiness,
                "sleep": pet.sleep,
                "health": pet.health,
                "born": pet.born,
                "age": await get_age(pet.id),
                "last_game": await get_data(pet.id).get("last_game"),
                "state": pet.state,
                "status": status,
            }
            if pet.status == "dead":
                data["death"] = pet.death
            return data


async def start_play(id, game):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "nothing":
            pet.state = "playing"
            data = await get_data(pet.id)
            data["game"] = game
            pet.data = str(data)
            await session.commit()
            if data.get("last_game") == game:
                return False, messages['interfaces']['play']['last_game_used'].format(game)
            return True, ""
        return False, messages["pet"]["busy"]


async def break_play(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "playing":
            pet.state = "nothing"
            pet.happiness = max(pet.happiness - config["play"]["break_play_index"], 0)
            data = await get_data(pet.id)
            data["last_game"] = data["game"]
            pet.data = str(data)
            await session.commit()
            return True, ""
        return False, messages["pet"]["not_playing"]


async def play(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "playing":
            data = await get_data(id)
            last_game = data.get("last_game")
            game = data["game"]
            if last_game != game:
                pet.happiness = min(pet.happiness + config["play"]["play_index"], 100)
            else:
                happiness = round(
                    (pet.happiness + config["play"]["play_index"])
                    * (100 - config["play"]["play_again_index"])
                    // 100
                )
                pet.happiness = min(happiness, 100)
            if pet.happiness == 100:
                pet.state = 'nothing'
                await user_send(pet.user_id, messages['interfaces']['play']['finally'])
            await session.commit()


async def feed(id, food):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "nothing":
            for key, value in config["food"].items():
                if value["name"] == food:
                    index = value["feed_index"]
            pet.satiety = min(pet.satiety + index, 100)
            await session.commit()
            return True, ""
        return False, messages["pet"]["busy"]


async def start_sleep(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "nothing" and pet.sleep <= config['sleep']['min_sleep_index']:
            pet.state = "sleeping"
            await session.commit()
            return True, ""
        if pet.sleep > config['sleep']['min_sleep_index']:
            return False, messages['interfaces']['sleep']['min_sleep']
        return False, messages["pet"]["busy"]


async def break_sleep(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "sleeping":
            pet.state = "nothing"
            pet.happiness -= config["sleep"]["break_sleep_index"]
            await session.commit()
            return True, ""
        return False, messages["pet"]["not_sleeping"]


async def sleep(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet and pet.state == "sleeping":
            pet.health = min(pet.health + config["sleep"]["health_sleep_index"], 100)
            pet.sleep = min(pet.sleep + config["sleep"]["sleep_index"], 100)
            if pet.sleep == 100:
                pet.state = 'nothing'
                await user_send(pet.user_id, messages['interfaces']['sleep']['finally'])
            await session.commit()


async def check_indexes(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == "live"))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.satiety <= 0:
                await health(id, config['food']['zero_health_index'], False)
            if pet.happiness <= 0:
                await health(id, config['play']['zero_health_index'], False)
            if pet.sleep <= 0:
                await health(id, config['sleep']['zero_health_index'], False)
            if pet.health <= 0:
                await die(id)
            await session.commit()


# Automatic updates
async def edit_pet():
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.status == "live"))
        pets = result.scalars().all()
        for pet in pets:
            await hunger(pet.id)
            await sadness(pet.id)
            await sleep_down(pet.id)
            await play(pet.id)
            await sleep(pet.id)
            await check_indexes(pet.id)


async def pet_tasks():
    while True:
        time = config["engine"]["time_of_last_check"]
        if time != "None":
            time = datetime.fromisoformat(time)
            time = time + timedelta(seconds=config["engine"]["pet_tasks_time"])
            if datetime.now() >= time:
                await edit_pet()
                config["engine"]["time_of_last_check"] = datetime.now().isoformat()
                with open(config_path, "w") as f:
                    yaml.dump(config, f, allow_unicode=True)
        else:
            config["engine"]["time_of_last_check"] = datetime.now().isoformat()
            with open(config_path, "w") as f:
                yaml.dump(config, f, allow_unicode=True)

        await asyncio.sleep(config["engine"]["pet_tasks_time"])
