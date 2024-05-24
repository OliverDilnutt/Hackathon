from core import config, logging, messages, bot, config_path
from core.database import Pet, AsyncSessionLocal, get_data, db, get_inventory
from core.utils import user_send, generate_markup

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

            files_pets = os.listdir(config["imgs"]["path_pets_folder"])
            files_rooms = os.listdir(config["imgs"]["path_rooms_folder"])
            files_panels = os.listdir(config["imgs"]["path_panels_folder"])
            files_backgrounds = os.listdir(config["imgs"]["path_backgrounds_folder"])
            files_eggs = os.listdir(config["imgs"]["path_eggs_folder"])

            random_pet = files_pets[random.randint(0, len(files_pets) - 1)]
            random_room = files_rooms[random.randint(0, len(files_rooms) - 1)]
            random_panel = files_panels[random.randint(0, len(files_panels) - 1)]
            random_background = files_backgrounds[random.randint(0, len(files_backgrounds) - 1)]
            random_egg = files_eggs[random.randint(0, len(files_eggs) - 1)]
            data = await get_data(pet.id)
            data["pet_img"] = random_pet
            data["room_img"] = random_room
            data['panel_img'] = random_panel
            data["background_img"] = random_background
            data["egg_img"] = random_egg
            pet.data = str(data)
            await session.commit()
            return True, ""
        return False, messages["errors"]["already_have_pet"]


async def hatching(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()

        if pet:
            data = await get_data(pet.id)
            data["start_hatching"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            timer = config["engine"]["hatching_timer"]
            pet.data = str(data)
            await session.commit()
        else:
            return False, messages["errors"]["not_have_pet"]
    asyncio.create_task(change_status_after_timer(id, timer))
    return True, ""


async def change_status_after_timer(id, timer):
    await asyncio.sleep(timer)
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()
        if pet:
            pet.status = "live"
            pet.born = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            await session.commit()
            await user_send(
                pet.user_id,
                messages["interfaces"]["hatching_finally"]["text"],
                await generate_markup(
                    messages["interfaces"]["hatching_finally"]["buttons"]
                ),
            )


async def save_pet_name(user_id, input):
    pet_name = input
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.user_id == user_id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if len(pet_name) <= 20:
                pet.name = pet_name
                await session.commit()
                return True, ""
            else:
                return False, messages["errors"]["name_too_long"]
        return False, messages["errors"]["not_have_pet"]


async def save_random_pet_name(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.user_id == user_id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            name = names.get_first_name()
            pet.name = name
            await session.commit()
            text = messages["interfaces"]["random_pet_name"]["text"]
            text = text.format(name)
            return True, text
        return False, messages["errors"]["not_have_pet"]


async def hunger(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if auto:
                pet.satiety = max(pet.satiety - config["food"]["hunger_index"], 0)
            else:
                pet.satiety = max(pet.satiety - index, 0)
            await session.commit()


async def sadness(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet and pet.state != "playing":
            if auto:
                pet.happiness = max(
                    pet.happiness - config["engine"]["sadness_index"], 0
                )
            else:
                pet.happiness = max(pet.happiness - index, 0)
            await session.commit()


async def sleep_down(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet and pet.state != "sleeping":
            if auto:
                pet.sleep = max(pet.sleep - config["sleep"]["sleep_down_index"], 0)
            else:
                pet.sleep = max(pet.sleep - index, 0)
            await session.commit()


async def health(id, index=None, auto=True):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
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
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            pet.status = "dead"
            pet.death = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            await session.commit()


async def get_info(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            status = (
                messages["statuses"]["live"]
                if pet.status == "live"
                else messages["statuses"]["dead"]
            )
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
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet and pet.state == "nothing":
            pet.state = "playing"
            data = await get_data(pet.id)
            data["game"] = game
            pet.data = str(data)
            await session.commit()
            if data.get("last_game") == game:
                return False, messages["interfaces"]["play"]["last_game_used"].format(
                    game
                )
            return True, ""
        return False, messages["pet"]["busy"]


async def break_play(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
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
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
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
                pet.state = "nothing"
                await user_send(pet.user_id, messages["interfaces"]["play"]["finally"])
            await session.commit()


async def feed(id, food, amount):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                if pet.state == "nothing":
                    inventory = await get_inventory(pet.id)
                    for key, value in config["food"]["list"].items():
                        if key == food:
                            index = value["feed_index"]
                            if food in inventory:
                                if amount.isdigit():
                                    amount = int(amount)
                                    if inventory[food]['amount'] - amount >= 0:
                                        inventory[food]['amount'] -= amount
                                        pet.satiety = min(pet.satiety + index, 100)
                                        pet.inventory = str(inventory)
                                        await session.commit()
                                        return True, ""
                                    else:
                                        return False, messages["errors"]["not_enough_food"]
                                else:
                                    return False, messages["errors"]["not_int"]
                            else:
                                return False, messages["errors"]["not_have_food"]
                else:
                    return False, messages["pet"]["busy"]
            else:
                return False, messages["errors"]["dead"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def start_sleep(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                if pet.state == "nothing":
                    if pet.sleep <= config["sleep"]["min_sleep_index"]:
                        pet.state = "sleeping"
                        await session.commit()
                        return True, ""
                    else:
                        return False, messages["interfaces"]["sleep"]["min_sleep"]
                else:
                    return False, messages["pet"]["busy"]
            else:
                return False, messages["pet"]["dead"]
        else:
            return False, messages["pet"]["not_have_pet"]


async def break_sleep(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet and pet.state == "sleeping":
            pet.state = "nothing"
            pet.happiness -= config["sleep"]["break_sleep_index"]
            await session.commit()
            return True, ""
        return False, messages["pet"]["not_sleeping"]


async def sleep(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet and pet.state == "sleeping":
            pet.health = min(pet.health + config["sleep"]["health_sleep_index"], 100)
            pet.sleep = min(pet.sleep + config["sleep"]["sleep_index"], 100)
            if pet.sleep == 100:
                pet.state = "nothing"
                await user_send(pet.user_id, messages["interfaces"]["sleep"]["finally"])
            await session.commit()


async def start_collect_food(id, amount):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                if pet.state == "nothing":
                    pet.state = "collecting"
                    data = await get_data(pet.id)
                    data["required_amount_collect_food"] = amount
                    data["collected_food"] = 0
                    pet.data = str(data)
                    await session.commit()
                    return True, ""
                else:
                    return False, messages["pet"]["busy"]
            else:
                return False, messages["pet"]["dead"]
        else:
            return False, messages["pet"]["not_have_pet"]


async def collect_food(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet and pet.state == "collecting":
            await hunger(config["food"]["collect_index"])
            data = await get_data(pet.id)
            inventory = await get_inventory(pet.id)

            food_list = []
            chances = []
            for food_name, food_data in config["food"]["list"].items():
                if food_data["can_find"]:
                    food_list.append(food_name)
                    chances.append(food_data["chance"])

            chosen_food = random.choices(food_list, weights=chances)[0]

            if random.random() < config["collect_food"]["chance"]:
                if data["collected_food"] < data["required_amount_collect_food"]:
                    data["collected_food"] += 1
                    now_amount = inventory.get(chosen_food)
                    if now_amount is not None:
                        now_amount = now_amount["amount"]
                    else:
                        now_amount = 0
                    inventory[chosen_food] = {
                        "name": config["food"]["list"][chosen_food]["name"],
                        "amount": now_amount + 1,
                        "class": "food",
                    }

                    if data["collected_food"] == data["required_amount_collect_food"]:
                        pet.state = "nothing"
                        await user_send(
                            pet.user_id,
                            messages["interfaces"]["collect_food"]["finally"],
                        )

                else:
                    pet.state = "nothing"
                    await user_send(
                        pet.user_id, messages["interfaces"]["collect_food"]["finally"]
                    )

                pet.data = str(data)
                pet.inventory = str(inventory)
                await session.commit()
                return True, ""


async def break_collect_food(id):
    from core.interface import parse_actions

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                if pet.state == "collecting":
                    pet.state = "nothing"
                    await session.commit()
                    data = await get_data(pet.id)
                    required = data["required_amount_collect_food"]
                    collected = data["collected_food"]

                    markup = await parse_actions(pet.user_id)

                    return True, messages["interfaces"]["break_collect_food"][
                        "text"
                    ].format(collected, required)
                else:
                    return False, messages["errors"]["not_collecting"]
            else:
                return False, messages["errors"]["dead"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def check_indexes(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(Pet).filter(Pet.id == id, Pet.status == "live")
        )
        pet = result.scalar_one_or_none()
        if pet:
            if pet.satiety <= 0:
                await health(id, config["food"]["zero_health_index"], False)
            if pet.happiness <= 0:
                await health(id, config["play"]["zero_health_index"], False)
            if pet.sleep <= 0:
                await health(id, config["sleep"]["zero_health_index"], False)
            if pet.health <= 0:
                await die(id)
            await session.commit()


async def final_hatching_after_restart(id):
    data = await get_data(id)
    start_hatching = datetime.strptime(
        data["start_hatching"], "%Y-%m-%d %H:%M:%S.%f"
    )
    now = datetime.now()
    elapsed_seconds = (now - start_hatching).seconds
    hatching_timer = config["engine"]["hatching_timer"]
    if elapsed_seconds >= hatching_timer:
        async with AsyncSessionLocal() as session:
            result = await session.execute(db.select(Pet).filter(Pet.id == id))
            pet = result.scalar_one_or_none()
            pet.status = "live"
            pet.born = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            await session.commit()
            await user_send(
                pet.user_id,
                messages["interfaces"]["hatching_finally"]["text"],
                await generate_markup(
                    messages["interfaces"]["hatching_finally"]["buttons"]
                ),
            )


async def lvl_up(id):
    time_start_activity = (await get_data(id))['time_start_activity']
    if time_start_activity // config['lvl']['lvl_up_for_activity_by_time'] > 1:
        async with AsyncSessionLocal() as session:
            result = await session.execute(db.select(Pet).filter(Pet.id == id))
            pet = result.scalar_one_or_none()
            if pet.state == 'playing':
                pet.experience += config['lvl']['playing']
                
            elif pet.state =='sleeping':
                pet.experience += config['lvl']['sleeping']
                
            elif pet.state == 'collecting':
                pet.experience += config['lvl']['collecting']
            
            experience_for_up_lvl = config['lvl']['experience'] * (1.1)**pet.lvl
            if pet.experience > experience_for_up_lvl:
                pet.lvl += 1
                pet.experience = 0

            await session.commit()

# Automatic updates
async def edit_pet():
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet))
        pets = result.scalars().all()
        for pet in pets:
            if pet.status == "hatching":
                await final_hatching_after_restart(pet.id)
            if pet.status == "live":
                await hunger(pet.id)
                await sadness(pet.id)
                await sleep_down(pet.id)
                await play(pet.id)
                await sleep(pet.id)
                await check_indexes(pet.id)
                await collect_food(pet.id)


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
