from core import config, logging, messages, bot, morph, config_path, inventory_items
from core.database import Pet, AsyncSessionLocal, get_data, db, get_inventory
from core.utils import user_send, generate_markup, save_time_start_activity

from datetime import datetime, timedelta
import asyncio
import yaml
import names
import os
import random


async def new_pet(user_id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
            pet = result.scalar_one_or_none()
            if not pet:
                pet = Pet(user_id=user_id)
                session.add(pet)
                # await session.commit()  # Сначала сохраняем питомца, чтобы получить его id
                
                # # Получаем id только что сохраненного питомца
                # await session.refresh(pet)
                
                files_pets = os.listdir(config["imgs"]["path_pets_folder"])
                files_rooms = os.listdir(config["imgs"]["path_rooms_folder"])
                files_panels = os.listdir(config["imgs"]["path_panels_folder"])
                files_backgrounds = os.listdir(config["imgs"]["path_backgrounds_folder"])
                files_eggs = os.listdir(config["imgs"]["path_eggs_folder"])

                random_pet = files_pets[random.randint(0, len(files_pets) - 1)]
                random_room = files_rooms[random.randint(0, len(files_rooms) - 1)]
                random_panel = files_panels[random.randint(0, len(files_panels) - 1)]
                random_background = files_backgrounds[
                    random.randint(0, len(files_backgrounds) - 1)
                ]
                random_egg = files_eggs[random.randint(0, len(files_eggs) - 1)]
                
                # Теперь, когда pet сохранен в базу данных и имеет свой id, можно использовать его id
                data = await get_data(pet.id)
                data["pet_img"] = random_pet
                data["room_img"] = random_room
                data["panel_img"] = random_panel
                data["background_img"] = random_background
                data["egg_img"] = random_egg
                data["education"] = 0
                pet.data = str(data)
                await session.commit()
                return True, ""
            return False, messages["errors"]["already_have_pet"]



async def hatching(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
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
        async with session.begin_nested():
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
        async with session.begin_nested():
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
        async with session.begin_nested():
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


async def hunger(id, index=None, auto=True):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
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


async def satiety(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                if auto:
                    pet.satiety = min(pet.satiety + config["food"]["satiety_index"], 100)
                else:
                    pet.satiety = min(pet.satiety + index, 100)
                await session.commit()


async def sadness(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
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


async def happiness(id, index=None, auto=True):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet and pet.state != "playing":
                if auto:
                    pet.happiness = min(
                        pet.happiness + config["engine"]["happiness_index"], 100
                    )
                else:
                    pet.happiness = min(pet.happiness + index, 100)
                await session.commit()


async def sleep_down(id, auto=True, index=None):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet and pet.state not in ["sleeping", "playing"]:
                if auto:
                    pet.sleep = max(pet.sleep - config["sleep"]["sleep_down_index"], 0)
                else:
                    pet.sleep = max(pet.sleep - index, 0)
                await session.commit()


async def health(id, index=None, auto=True):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                if auto:
                    pet.health = min(pet.health + config["engine"]["health_index"], 100)
                else:
                    if index > 0:
                        pet.health = min(pet.health + index, 100)
                    else:
                        pet.health = max(pet.health + index, 0)
                await session.commit()


# async def get_age(id):
#     async with AsyncSessionLocal() as session:
#         result = await session.execute(db.select(Pet).filter(Pet.id == id))
#         pet = result.scalar_one_or_none()
#         if pet:
#             born = datetime.strptime(pet.born, "%Y-%m-%d %H:%M:%S.%f")
#             if pet.status == "live":
#                 age = datetime.now() - born
#             else:
#                 death = datetime.strptime(pet.death, "%Y-%m-%d %H:%M:%S.%f")
#                 age = death - born
#             if age.days > 0:
#                 return age.days, "days"
#             elif age.seconds // 3600 > 0:
#                 return age.seconds // 3600, "hours"
#             elif age.seconds // 60 > 0:
#                 return age.seconds // 60, "minutes"
#             else:
#                 return age.seconds, "seconds"


async def get_age(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()
        if pet:
            born = datetime.strptime(pet.born, "%Y-%m-%d %H:%M:%S.%f")
            if pet.status == "live":
                now = datetime.now()
            else:
                death = datetime.strptime(pet.death, "%Y-%m-%d %H:%M:%S.%f")
                now = death

            delta = now - born

            days = delta.days
            seconds = delta.seconds

            months = (now.year - born.year) * 12 + now.month - born.month
            if now.day < born.day:
                months -= 1

            days_in_current_month = (now.replace(day=1) - timedelta(days=1)).day
            days = min(days_in_current_month, days)

            weeks, days = divmod(days, 7)
            hours, seconds = divmod(seconds, 3600)
            minutes, seconds = divmod(seconds, 60)

            time_parts = []

            if months > 0:
                agreed_word = morph.parse("месяц")[0].make_agree_with_number(months).word
                time_parts.append(f"{months} {agreed_word}")
            if weeks > 0:
                agreed_word = morph.parse("неделя")[0].make_agree_with_number(weeks).word
                time_parts.append(f"{weeks} {agreed_word}")
            if days > 0:
                agreed_word = morph.parse("день")[0].make_agree_with_number(days).word
                time_parts.append(f"{days} {agreed_word}")
            if hours > 0:
                agreed_word = morph.parse("час")[0].make_agree_with_number(hours).word
                time_parts.append(f"{hours} {agreed_word}")
            if minutes > 0:
                agreed_word = morph.parse("минута")[0].make_agree_with_number(minutes).word
                time_parts.append(f"{minutes} {agreed_word}")
            if seconds > 0:
                agreed_word = morph.parse("секунда")[0].make_agree_with_number(seconds).word
                time_parts.append(f"{seconds} {agreed_word}")

            return ' '.join(time_parts)


async def die(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                pet.status = "dead"
                pet.death = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                await session.commit()
                await user_send(
                    pet.user_id, messages["interfaces"]["death"]["text"].format(pet.name)
                )


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
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet and pet.state == "nothing":
                pet.state = "playing"
                await save_time_start_activity(id)
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
        async with session.begin_nested():
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
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live", Pet.state == "playing")
            )
            pet = result.scalar_one_or_none()
            
            if pet:
                data = await get_data(id)
                last_game = data.get("last_game")
                game = data["game"]
                game_id = next((game_id for game_id, game_info in config['games']["list"].items() if game_info["name"] == game), None)
                
                if game_id is not None:
                    happiness_increase = config["play"]["play_index"]
                    sleep_reduction = config["games"]['list'][game_id]["sleep"]
                    
                    if last_game == game:
                        happiness_increase = round(
                            happiness_increase * (100 - sleep_reduction) / 100
                        )
                    
                    pet.happiness = min(pet.happiness + happiness_increase, 100)
                    await sleep_down(pet.id, sleep_reduction, False)
                    
                    if pet.happiness == 100:
                        pet.state = "nothing"
                        await user_send(pet.user_id, messages["interfaces"]["play"]["finally"])
                    
                    await session.commit()



async def feed(id, food, amount):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            
            if not pet:
                return False, messages["errors"]["not_have_pet"]
            
            if pet.state != "nothing":
                return False, messages["pet"]["busy"]
            
            if pet.status != "live":
                return False, messages["errors"]["dead"]
            
            inventory = await get_inventory(pet.id)
            food_list = {key: value for key, value in inventory_items.items() if value["class"] == "food"}
            
            if food not in food_list:
                return False, messages["errors"]["not_have_food"]
            
            feed_index = food_list[food]["feed_index"]
            
            if amount.isdigit():
                amount = int(amount)
                if food in inventory:
                    if inventory[food]["amount"] >= amount:
                        inventory[food]["amount"] -= amount
                        pet.satiety = min(pet.satiety + feed_index * amount, 100)
                        pet.inventory = str(inventory)
                        await session.commit()
                        return True, ""
                    else:
                        return False, messages["errors"]["not_enough_food"]
                else:
                    return False, messages["errors"]["not_have_food"]
            else:
                return False, messages["errors"]["not_int"]



async def start_sleep(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                if pet.status == "live":
                    if pet.state == "nothing":
                        if pet.sleep <= config["sleep"]["min_sleep_index"]:
                            pet.state = "sleeping"
                            await save_time_start_activity(id)
                            await session.commit()
                            return True, ""
                        else:
                            return False, messages["interfaces"]["sleep"][
                                "min_sleep"
                            ].format(pet.name)
                    else:
                        return False, messages["pet"]["busy"]
                else:
                    return False, messages["errors"]["dead"]
            else:
                return False, messages["errors"]["not_have_pet"]


async def break_sleep(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
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


async def sleep(id, index=None, auto=True):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            
            if pet and pet.state == "sleeping":
                if auto:
                    pet.health = min(pet.health + config["sleep"]["health_sleep_index"], 100)
                    pet.sleep = min(pet.sleep + config["sleep"]["sleep_index"], 100)
                    
                    if pet.sleep == 100:
                        pet.state = "nothing"
                        await user_send(pet.user_id, messages["interfaces"]["sleep"]["finally"].format(pet.name))
                else:
                    if index < 0:
                        pet.sleep = max(pet.sleep - abs(index), 0)
                    else:
                        pet.sleep = min(pet.sleep + index, 100)

                await session.commit()



async def start_collect_food(id, amount):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                if pet.status == "live":
                    if pet.state == "nothing":
                        pet.state = "collecting"
                        await save_time_start_activity(id)
                        data = await get_data(pet.id)
                        data["required_amount_collect_food"] = amount
                        data["collected_food"] = 0
                        pet.data = str(data)
                        await session.commit()
                        return True, ""
                    else:
                        return False, messages["pet"]["busy"]
                else:
                    return False, messages["errors"]["dead"]
            else:
                return False, messages["errors"]["not_have_pet"]


async def collect_food(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live", Pet.state == "collecting")
            )
            pet = result.scalar_one_or_none()
            
            if pet:
                await hunger(id, config["food"]["collect_index"])
                data = await get_data(id)
                inventory = await get_inventory(id)

                all_food_list = {key: value for key, value in inventory_items.items() if value["class"] == "food" and value["can_find"]}
                food_list = list(all_food_list.keys())
                chances = [food_data["chance"] for food_data in all_food_list.values()]

                chosen_food = random.choices(food_list, weights=chances)[0]

                if random.random() < config["collect_food"]["chance"]:
                    if data["collected_food"] < data["required_amount_collect_food"]:
                        data["collected_food"] += 1
                        inventory[chosen_food] = {
                            "name": inventory_items[chosen_food]["name"],
                            "amount": inventory.get(chosen_food, {"amount": 0})["amount"] + 1,
                            "class": "food",
                        }

                        if data["collected_food"] == data["required_amount_collect_food"]:
                            pet.state = "nothing"
                            await user_send(pet.user_id, messages["interfaces"]["collect_food"]["finally"])

                    else:
                        pet.state = "nothing"
                        await user_send(pet.user_id, messages["interfaces"]["collect_food"]["finally"])

                    pet.data = str(data)
                    pet.inventory = str(inventory)
                    await session.commit()
                    return True, ""


async def break_collect_food(id):
    from core.interface import parse_actions

    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
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
                        
                        return True, messages["interfaces"]["break_collect_food"][
                            "text"
                        ].format(collected, required)
                    else:
                        return False, messages["errors"]["not_collecting"]
                else:
                    return False, messages["errors"]["dead"]
            else:
                return False, messages["errors"]["not_have_pet"]


async def start_journey(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                if pet.status == "live":
                    if pet.state == "nothing":
                        pet.state = "traveling"
                        await save_time_start_activity(id)
                        await session.commit()
                        return True, ""
                    else:
                        return False, messages["pet"]["busy"]
                else:
                    return False, messages["errors"]["dead"]
            else:
                return False, messages["pet"]["not_have_pet"]


async def travel(id):
    from core.interface import finally_journey

    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(db.select(Pet).filter(Pet.id == id, Pet.status == 'live', Pet.state == "traveling"))
            pet = result.scalar_one_or_none()
            if pet:
                data = await get_data(id)
                duration = data["journey_duration"]
                time_start = datetime.strptime(
                    data["time_start_activity"], "%Y-%m-%d %H:%M:%S.%f"
                )
                if datetime.now() - time_start > timedelta(minutes=duration):
                    pet.state = "nothing"
                    await user_send(
                        pet.user_id, messages["interfaces"]["journey"]["finally"]
                    )
                    status, events_text = await finally_journey(pet.user_id)
                    await session.commit()
                    if status:
                        await user_send(pet.user_id, events_text)
                        return
                location = data["journey_location"]

                if random.random() < config["journey"]["event_in_journey"]:
                    if pet.health > config["journey"]["min_health"]:
                        event = random.choice(
                            list(
                                messages["events"]["journey"][location][
                                    "events"
                                ].values()
                            )
                        )
                    else:
                        good_events = {
                            key: value
                            for key, value in messages["events"]["journey"][
                                location
                            ]["events"].items()
                            if value["class"] == "good"
                        }
                        event = random.choice(good_events)
                    changes = event["changes"]

                    # Обновление состояния питомца на основе изменений из события
                    if "health" in changes:
                        await health(id, changes["health"], False)
                    if "satiety" in changes:
                        await hunger(id, changes["satiety"], False)
                    if "happiness" in changes:
                        await happiness(id, changes["happiness"], False)
                    if "sleep" in changes:
                        await sleep(id, changes["sleep"], False)

                    if "events" not in data:
                        data["events"] = []
                    data["events"].append(event)

                    # Если есть найденные предметы, добавляем их в инвентарь
                    if "found" in changes:
                        inventory = await get_inventory(pet.id)
                        for item in changes["found"]:
                            for name, amount in item.items():
                                inventory[
                                    next(
                                        (
                                            item_name
                                            for item_name, item_data in inventory_items.items()
                                            if name == item_data["name"]
                                        ),
                                        None,
                                    )
                                ] = {
                                    "name": name,
                                    "amount": amount,
                                    "class": next(
                                        (
                                            item_data["class"]
                                            for item_name, item_data in inventory_items.items()
                                            if name == item_data["name"]
                                        ),
                                        None,
                                    ),
                                }
                        pet.inventory = str(inventory)
                    pet.data = str(data)

                    await session.commit()



async def break_journey(id):
    from core.interface import finally_journey

    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                if pet.state == "traveling":
                    pet.stata = "nothing"
                    await user_send(
                        pet.user_id, messages["interfaces"]["back_home"]["text"]
                    )
                    status, events_text = await finally_journey(pet.user_id)
                    if status:
                        await user_send(pet.user_id, events_text)
                else:
                    return False, messages["pet"]["not_traveling"]
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


async def final_hatching_after_restart(id):
    data = await get_data(id)
    start_hatching = data.get("start_hatching")
    if start_hatching != None:
        start_hatching = datetime.strptime(start_hatching, "%Y-%m-%d %H:%M:%S.%f")
        now = datetime.now()
        elapsed_seconds = (now - start_hatching).seconds
        hatching_timer = config["engine"]["hatching_timer"]
        if elapsed_seconds >= hatching_timer:
            async with AsyncSessionLocal() as session:
                async with session.begin_nested():
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


async def level_up(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(db.select(Pet).filter(Pet.id == id))
            pet = result.scalar_one_or_none()
            if pet:
                data = await get_data(id)
                time_start_activity = data.get("time_start_activity")
                if time_start_activity:
                    time_start_activity = datetime.strptime(time_start_activity, '%Y-%m-%d %H:%M:%S.%f')
                    current_time = datetime.now()
                    activity_duration = (current_time - time_start_activity).total_seconds()
                    if activity_duration // config["level"]["level_up_for_activity_by_time"] > 1:
                        experience_gain = config["level"].get(pet.state, config["level"]["nothing"])
                        pet.experience += experience_gain

                        experience_for_up_level = round(config["level"]["experience"] * (1.1) ** pet.level)
                        if pet.experience > experience_for_up_level:
                            pet.level += 1
                            pet.experience = 0
                            await user_send(
                                pet.user_id,
                                messages["notifications"]["level_up"].format(pet.level)
                            )

                        education_buff = data["education"] // 10
                        pet.experience += min(education_buff, config["level"]["max_education_buff"])

                        # Проверяем, изменились ли данные перед коммитом
                        if session.is_modified(pet):
                            await session.commit()




async def notifications(id):
    async with AsyncSessionLocal() as session:
        async with session.begin_nested():
            result = await session.execute(
                db.select(Pet).filter(Pet.id == id, Pet.status == "live")
            )
            pet = result.scalar_one_or_none()
            if pet:
                data = await get_data(id)
                last_notification = data.get("last_notification")
                now = datetime.now()
                if last_notification is None or now - datetime.strptime(
                    last_notification, "%Y-%m-%d %H:%M:%S.%f"
                ) > timedelta(minutes=config["engine"]["notification_time"]):
                    notification_sent = False
                    if pet.health < config["engine"]["health_min_value"]:
                        await user_send(
                            pet.user_id,
                            messages["notifications"]["min_value_health"].format(
                                config["engine"]["health_min_value"]
                            ),
                        )
                        notification_sent = True
                    if pet.satiety < config["food"]["min_value"]:
                        await user_send(
                            pet.user_id,
                            messages["notifications"]["min_value_satiety"].format(
                                config["food"]["min_value"]
                            ),
                        )
                        notification_sent = True
                    if pet.happiness < config["play"]["min_value"]:
                        await user_send(
                            pet.user_id,
                            messages["notifications"]["min_value_play"].format(
                                config["play"]["min_value"]
                            ),
                        )
                        notification_sent = True
                    if pet.sleep < config["sleep"]["min_value"]:
                        await user_send(
                            pet.user_id,
                            messages["notifications"]["min_value_sleep"].format(
                                config["sleep"]["min_value"]
                            ),
                        )
                        notification_sent = True

                    if notification_sent:
                        data["last_notification"] = now.strftime("%Y-%m-%d %H:%M:%S.%f")
                        pet.data = str(data)
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
                await health(pet.id)
                await check_indexes(pet.id)
                await collect_food(pet.id)
                await travel(pet.id)
                await level_up(pet.id)
                await notifications(pet.id)


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
