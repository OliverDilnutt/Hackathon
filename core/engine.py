from core import config, logging, messages, bot, config_path
from core.database import Pet, Session, get_data

from datetime import datetime, timedelta
import asyncio
import yaml
import names


async def new_pet(
    user_id,
):  # костыль из-за того что я не знаю как он user_id перейти к id животного (чтобы понял более точно проблему, см interface.py, функцию show_scene, там где выполнение функции)
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if not pet:
        pet = Pet(user_id=user_id)
        session.add(pet)
        session.commit()
        session.close()
        return True, ""
    else:
        session.close()
        return False, messages["errors"]["already_have_pet"]


async def save_pet_name(user_id, input):
    pet_name = input
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        pet.name = pet_name
        session.commit()
        session.close()
        return True, ""
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]


async def save_random_pet_name(user_id):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        name = names.get_first_name()
        pet.name = name
        session.commit()
        session.close()
        text = messages['interfaces']["random_pet_name"]["text"]
        text = text.format(name)
        return True, text
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]


async def hunger(id, auto=True, index=None):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    if auto:
        pet.satiety = max(pet.satiety - config["food"]["hunger_index"], 0)
    else:
        pet.satiety = max(pet.satiety - index, 0)

    session.commit()
    session.close()


async def sadness(id, auto=True, index=None):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()
    if pet.state != 'playing':
        if auto:
            pet.happiness = max(pet.happiness - config["engine"]["sadness_index"], 0)
        else:
            pet.happiness = max(pet.happiness - index, 0)

        session.commit()
        session.close()

async def sleep_down(id, auto=True, index=None):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()
    if pet.state != 'sleeping':
        if auto:
            pet.sleep = max(pet.sleep - config["sleep"]["sleep_down_index"], 0)
        else:
            pet.sleep = max(pet.sleep - index, 0)

        session.commit()
        session.close()


async def health(id, index=None, auto=True):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    if auto:
        pet.health = pet.health - config["engine"]["health_index"]
    else:
        pet.health = pet.health - index

    session.commit()
    session.close()


async def get_age(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    born = datetime.strptime(pet.born, "%Y-%m-%d %H:%M:%S.%f")

    age = datetime.now() - born

    session.close()

    if age.days > 0:
        return age.days, "days"
    elif age.seconds // 3600 > 0:
        return age.seconds // 3600, "hours"
    elif age.seconds // 60 > 0:
        return age.seconds // 60, "minutes"
    else:
        return age.seconds, "seconds"


async def die(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    pet.status = "dead"
    pet.death = datetime.now()

    session.commit()
    session.close()


async def get_info(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    session.close()

    if pet.status == "live":
        status = messages["statuses"]["live"]

    elif pet.status == "dead":
        status = messages["statuses"]["dead"]

    data = {
        "id": pet.id,
        "name": pet.name,
        "satiety": pet.satiety,
        "happiness": pet.happiness,
        "sleep": pet.sleep,
        "health": pet.health,
        "born": pet.born,
        "age": await get_age(pet.id),
        "last_game": await get_data(pet.id)["last_game"],
        "state": pet.state,
        "status": status,
    }

    if pet.status == "dead":
        data["death"] = pet.death

    return data
    

async def start_play(id, game):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    if pet.state == "nothing":
        pet.state = "playing"
        data = await get_data(pet.id)
        data["game"] = game
        pet.data = str(data)
        
        session.commit()
        session.close()
        if data.get("last_game") == game:
            return False, messages['interfaces']['play']['last_game_used'].format(game)
        else:
            return True, ""
    else:
        session.close()
        return False, messages["pet"]["busy"]


async def break_play(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()
    if pet.state == "playing":
        pet.state = "nothing"
        pet.happiness = max(pet.happiness - config["play"]["break_play_index"], 0)
        data = await get_data(pet.id)
        data["last_game"] = data["game"]
        pet.data = str(data)
        session.commit()
        session.close()
        return True, ""
    else:
        session.close()
        return False, messages["pet"]["not_playing"]


async def play(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    if pet.state == "playing":
        data = await get_data(id)
        if data.get("last_game") is not None:
            last_game = data["last_game"]
        else:
            last_game = None
        game = data["game"]
        if last_game != game:
            pet.happiness = min(pet.happiness + config["play"]["play_index"], 100)

        else:
            happiness = (
                (pet.happiness - config["play"]["play_index"])
                * (100 - config["play"]["play_again_index"])
                // 100
            )
            pet.happiness = min(happiness, 100)

        session.commit()
        session.close()


async def feed(id, food):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    if pet.state == "nothing":
        for key, value in config["food"].items():
            if value["name"] == food:
                index = value["feed_index"]

        pet.satiety = min(pet.satiety + index, 100)
        session.commit()
        session.close()
        return True, ""
    else:
        return False, messages["pet"]["busy"]


async def start_sleep(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()
    if pet.state == "nothing":
        pet.state = "sleeping"

        session.commit()
        session.close()
        return True, ""
    else:
        session.close()
        return False, messages["pet"]["busy"]


async def break_sleep(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()
    if pet.state == "sleeping":
        pet.state = "nothing"
        pet.happiness -= config["sleep"]["break_sleep_index"]

        session.commit()
        session.close()
        return True, ""
    else:
        session.close()
        return False, messages["pet"]["not_sleeping"]


async def sleep(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()
    if pet.state == "sleeping":
        pet.health = min(pet.health + config["engine"]["health_sleep_index"], 100)
        pet.sleep = min(pet.sleep + config["engine"]["sleep_index"], 100)

        session.commit()
        session.close()



async def check_indexes(id):
    session = Session()

    pet = session.query(Pet).filter(Pet.id == id and Pet.status == "live").first()

    if pet.satiety <= 0:
        await health(id, config['food']['zero_health_index'], False)
    if pet.happiness <= 0:
        await health(id, config['games']['zero_health_index'], False)
    if pet.sleep <= 0:
        await health(id, config['sleep']['zero_health_index'], False)
    if pet.health <= 0:
        await die(id)

    session.commit()
    session.close()


# Automatic updates
async def edit_pet():
    session = Session()

    pets = session.query(Pet).filter(Pet.status == "live").all()
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
