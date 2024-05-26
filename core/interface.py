from datetime import datetime
from math import ceil
import random
import re

from core import config, messages, morph, bot, inventory_items
from core.database import (
    AsyncSessionLocal,
    Pet,
    States,
    new_user,
    db,
    get_data,
    get_inventory,
)

from core.utils import (
    generate_markup,
    create_info_image,
    egg_show,
    get_current_page,
    generate_paginated_markup,
    update_current_category,
    update_current_page,
    get_player_rank,
    user_send,
    journey_images,
    get_index_state,
)
from core.engine import (
    new_pet,
    save_pet_name,
    save_random_pet_name,
    start_play,
    break_play,
    get_age,
    start_sleep,
    break_sleep,
    feed,
    start_collect_food,
    break_collect_food,
    hatching,
    start_journey,
)


async def check_triggers(user_id, text):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(States).filter(States.user_id == user_id)
        )
        state = result.scalar_one_or_none()

        for interface_name, interface_data in messages["interfaces"].items():
            if text in interface_data["trigger"]:
                return True, False, interface_name
        else:
            if state is not None and state.state is not None:
                return True, text, interface_name
            else:
                return False, False, messages["interfaces"]["not_found"]["text"]


async def show_interface(user_id, interface_name, input=False):
    text = messages["interfaces"][interface_name]["text"]
    img = messages["interfaces"][interface_name]["img"]
    markup = messages["interfaces"][interface_name]["buttons"]
    buttons_in_row = messages["interfaces"][interface_name].get("buttons_in_row")
    func = messages["interfaces"][interface_name]["func"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()

    if (
        not "https://" in img
        or "http://" in img
        or "/" in img
        or "." in img
        and img != "None"
    ):
        img_func = globals().get(img)
        if img_func:
            status, img = await img_func(user_id=user_id)

            if not status:
                img = "None"

    if func != "None":
        function_to_call = globals().get(func)
        if function_to_call:
            if not input:
                status, func_text = await function_to_call(user_id=user_id)
            else:
                status, func_text = await function_to_call(user_id=user_id, input=input)

            if status:
                if func_text is not None and func_text != "" and func_text != "None":
                    text = func_text
            else:
                text = func_text
                return text, "None", "None"

    if type(markup) is not list:
        markup_func = globals().get(markup)
        if markup_func:
            if buttons_in_row is not None:
                markup = await markup_func(
                    user_id=user_id, buttons_in_row=buttons_in_row
                )
            else:
                markup = await markup_func(user_id=user_id)
    else:
        if buttons_in_row is not None:
            markup = await generate_markup(markup, buttons_in_row=buttons_in_row)
        else:
            markup = await generate_markup(markup)

    if text == messages["errors"]["not_have_pet"] and pet is None:
        text = messages["errors"]["not_have_pet"]
        img = "None"
        markup = await generate_markup(messages["buttons"]["not_have_pet"])
    elif (
        pet
        and pet.status == "hatching"
        and interface_name not in ["start", "start_game", "hatching", "user_info"]
    ):
        status, text = await hatching_check_interface(user_id)
        status, img = await egg_show(user_id)
        markup = await parse_hatching_check(user_id)
    return text, img, markup


async def parse_hatching_check(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "hatching":
                buttons = messages["buttons"]["hatching"]["in_time"]
                markup = await generate_markup(buttons)
                return markup
            else:
                buttons = messages["buttons"]["hatching"]["out_of_time"]
                markup = await generate_markup(buttons)
                return markup


async def parse_start_button(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "hatching":
                buttons = messages["buttons"]["start"]["normal"]
                markup = await generate_markup(buttons)
                return markup
            else:
                buttons = messages["buttons"]["start"]["already_reg"]
                markup = await generate_markup(buttons)
                return markup
        else:
            buttons = messages["buttons"]["start"]["normal"]
            markup = await generate_markup(buttons)
            return markup


async def parse_actions(user_id, buttons_in_row=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                buttons = messages["buttons"]["actions_buttons"][pet.state]
                markup = await generate_markup(buttons)
                return markup


async def parse_games(user_id, buttons_in_row=None):
    await update_current_category(user_id, "games")
    games = config["games"]["list"]
    game_names_list = [games[game]["name"] for game in games]

    items_per_page = messages["buttons"]["items_per_page"]
    current_page = await get_current_page(user_id)

    markup = await generate_paginated_markup(
        game_names_list, current_page, items_per_page, buttons_in_row
    )
    return markup


async def parse_food(user_id, buttons_in_row=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        await update_current_category(user_id, "food")
        foods = await get_inventory(pet.id)
        foods = [
            f"{value['name']} [{value['amount']}]"
            for key, value in foods.items()
            if value["class"] == "food" and value["amount"] > 0
        ]

        items_per_page = messages["buttons"]["items_per_page"]
        current_page = await get_current_page(user_id)

        markup = await generate_paginated_markup(
            foods, current_page, items_per_page, buttons_in_row
        )
        return markup

    else:
        return await generate_markup(messages["buttons"]["main_menu"])


async def parse_food_amount(user_id, buttons_in_row=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        if pet.status == "live" and pet.status != "hatching":
            food = (await get_data(pet.id))["selected_food"]
            food_amount = (await get_inventory(pet.id))[food]["amount"]
            buttons = []

            feed_index = config["food"]["list"][food]["feed_index"]
            max_amount = min(ceil((100 - pet.satiety) / int(feed_index)), food_amount)

            button_text = messages["interfaces"]["select_amount_food"]["buttons_style"]

            buttons.append(button_text.format(1, min(pet.satiety + feed_index, 100)))
            if food_amount > 2 and pet.satiety + feed_index < 100:
                buttons.append(
                    button_text.format(
                        round((max_amount + 1) / 2),
                        (
                            min(
                                pet.satiety
                                + (round((max_amount + 1) / 2) * feed_index),
                                100,
                            )
                        ),
                    )
                )
                if (
                    min(pet.satiety + (round((max_amount + 1) / 2) * feed_index), 100)
                    < 100
                ):
                    buttons.append(
                        button_text.format(
                            max_amount, min(pet.satiety + max_amount * feed_index, 100)
                        )
                    )

            actions = [messages["buttons"]["actions"]]
            if buttons_in_row is not None:
                markup = await generate_markup(
                    buttons,
                    buttons_in_row=buttons_in_row,
                    special_buttons=actions,
                    special_buttons_in_row=1,
                )
            else:
                markup = await generate_markup(
                    buttons, special_buttons=actions, special_buttons_in_row=1
                )
            return markup
    else:
        return await generate_markup(messages["buttons"]["main_menu"])


async def parse_locations(user_id, buttons_in_row=None):
    await update_current_category(user_id, "locations")
    location_names = [
        messages["events"]["journey"][location]["name"]
        for location in messages["events"]["journey"]
    ]

    items_per_page = messages["buttons"]["items_per_page"]
    current_page = await get_current_page(user_id)

    markup = await generate_paginated_markup(
        location_names, current_page, items_per_page, buttons_in_row
    )
    return markup


async def hatching_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "hatching":
                status, text = await hatching(pet.id)
                if status:
                    return True, ""
                else:
                    return False, text
            else:
                return False, messages["interfaces"]["hatching_check"]["out_of_time"]


async def hatching_check_interface(user_id, for_img=False):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            start_hatching = datetime.strptime(
                data["start_hatching"], "%Y-%m-%d %H:%M:%S.%f"
            )
            now = datetime.now()
            elapsed_seconds = (now - start_hatching).seconds
            hatching_timer = config["engine"]["hatching_timer"]

            if elapsed_seconds < hatching_timer:
                remaining_seconds = hatching_timer - elapsed_seconds
                remaining_minutes = remaining_seconds // 60
                remaining_seconds %= 60

                minute_name = messages["time_names"]["minutes"]
                second_name = messages["time_names"]["seconds"]
                agreed_word_minutes = (
                    morph.parse(minute_name)[0]
                    .make_agree_with_number(remaining_minutes)
                    .word
                )
                agreed_word_seconds = (
                    morph.parse(second_name)[0]
                    .make_agree_with_number(remaining_seconds)
                    .word
                )
                if for_img:
                    text = messages["interfaces"]["hatching_check"]["for_img"].format(
                        remaining_minutes,
                        "м.",
                        remaining_seconds,
                        "с.",
                    )
                else:
                    text = messages["interfaces"]["hatching_check"]["text"].format(
                        remaining_minutes,
                        agreed_word_minutes,
                        remaining_seconds,
                        agreed_word_seconds,
                    )
                return True, text
            return False, messages["interfaces"]["hatching_check"]["out_of_time"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def format_pet_info(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status != "hatching":
                text = messages["interfaces"]["main_menu"]["text"]
                age = await get_age(pet.id)
                age_time_name = messages["time_names"][age[1]]
                agreed_word = morph.parse(age_time_name)[0]
                agreed_word = agreed_word.make_agree_with_number(age[0]).word

                health_state = await get_index_state(pet.health, "health")
                satiety_state = await get_index_state(pet.satiety, "satiety")
                happiness_state = await get_index_state(pet.happiness, "happiness")
                sleep_state = await get_index_state(pet.sleep, "sleep")

                text = text.format(
                    pet.name,
                    messages["statuses"][pet.status],
                    messages["states"][pet.state],
                    f"{age[0]} {agreed_word}",
                    health_state,
                    pet.health,
                    satiety_state,
                    pet.satiety,
                    happiness_state,
                    pet.happiness,
                    sleep_state,
                    pet.sleep,
                )
                return True, text
            else:
                return False, messages["errors"]["not_hatch"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def start_sleep_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            status, text = await start_sleep(pet.id)
            if status:
                return True, ""
            else:
                return False, text
        else:
            return False, messages["errors"]["not_have_pet"]


async def break_sleep_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            await break_sleep(pet.id)
            return True, ""
        else:
            return False, messages["errors"]["not_have_pet"]


async def start_play_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            for name, data in config["games"]["list"].items():
                if input in data["name"]:
                    status, text = await start_play(pet.id, input)
                    if status:
                        text = messages["interfaces"]["play"]["text"].format(input)
                        return True, text
                    else:
                        return False, text
            else:
                return False, messages["errors"]["game_not_found"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def break_play_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            await break_play(pet.id)
            return True, ""
        else:
            return False, messages["errors"]["not_have_pet"]


async def save_selected_food(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live" and pet.status != "hatching":
                food_list = {
                    key: value
                    for key, value in inventory_items.items()
                    if value["class"] == "food"
                }
                food_found = False
                for name, data in food_list.items():
                    if input in data["name"]:
                        food_found = True
                        data = await get_data(pet.id)
                        data["selected_food"] = name
                        pet.data = str(data)
                        await session.commit()
                        return True, ""
                if not food_found:
                    return False, messages["errors"]["food_not_found"]
            else:
                return False, messages["errors"]["dead"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def feed_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live" and pet.status != "hatching":
                data = await get_data(pet.id)
                food = data["selected_food"]
                status, text = await feed(pet.id, food, input)
                if status:
                    return True, ""
                else:
                    return False, text
            else:
                return False, messages["errors"]["dead"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def start_collect_food_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if input.isdigit():
                amount = int(input)
                if amount <= config["collect_food"]["max_collect_food"]:
                    status, text = await start_collect_food(pet.id, amount)
                    if status:
                        return True, ""
                    else:
                        return False, text
                else:
                    return False, messages["errors"][
                        "too_much_food_for_collect"
                    ].format(config["collect_food"]["max_collect_food"])
            else:
                return False, messages["errors"]["not_int"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def progress_collect_food_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.state == "collecting":
                data = await get_data(pet.id)
                text = messages["interfaces"]["progress_collect_food"]["text"].format(
                    data["collected_food"], data["required_amount_collect_food"]
                )
                return True, text
            else:
                return False, messages["errors"]["not_collecting"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def break_collect_food_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        status, text = await break_collect_food(pet.id)

        if status:
            return True, text
        else:
            return False, text
    else:
        return False, messages["errors"]["not_have_pet"]


async def get_inventory_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            inventory = await get_inventory(pet.id)
            text = messages["interfaces"]["inventory"]["text"]
            if inventory != {}:
                for item_name, item_data in inventory.items():
                    text += messages["interfaces"]["inventory"]["item_text"].format(
                        item_data["name"], item_data["amount"]
                    )
            else:
                text = messages["interfaces"]["inventory"]["not_items"]
            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]


async def user_info(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            user = await bot.get_chat(user_id)

            if pet.status != "hatching":
                inventory = await get_inventory(pet.id)
                items_amount = 0
                for item_name, item_data in inventory.items():
                    items_amount += item_data["amount"]

                age = await get_age(pet.id)
                age_time_name = messages["time_names"][age[1]]
                agreed_word = morph.parse(age_time_name)[0]
                agreed_word = agreed_word.make_agree_with_number(age[0]).word
                age = f"{age[0]} {agreed_word}"

                text = messages["interfaces"]["user_info"]["text"].format(
                    user.username,
                    user.id,
                    pet.name,
                    messages["statuses"][pet.status],
                    pet.level,
                    pet.experience,
                    age,
                    items_amount,
                )
            else:
                text = messages["interfaces"]["user_info"]["not_hatching_text"].format(
                    user.username, user.id, messages["statuses"][pet.status]
                )
            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]


async def ranking(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet))
        pets = result.scalars().all()
        sorted_pets = sorted(pets, key=lambda pet: (-pet.level, -pet.experience))
        user_send_rank = await get_player_rank(user_id, sorted_pets)
        text = messages["interfaces"]["rank"]["text"].format(user_send_rank)
        for pet in sorted_pets:
            user = await bot.get_chat(pet.user_id)
            text += messages["interfaces"]["rank"]["user_text"].format(
                user.username, pet.level, pet.experience
            )

        return True, text


async def about_locations_interface(user_id):
    text = messages["interfaces"]["journey"]["text"]

    for location_name, location_data in messages["events"]["journey"].items():
        text += messages["interfaces"]["journey"]["location_text"].format(
            location_data["name"], location_data["description"]
        )

    return True, text


async def select_location_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            for location_name, location_data in messages["events"]["journey"].items():
                if location_data["name"] == input:
                    data["journey_location"] = location_name
            pet.data = str(data)
            await session.commit()
            return True, ""
        else:
            return False, messages["errors"]["not_have_pet"]


async def finally_journey(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            events = data.get("events")
            if events is None:
                return True, messages["errors"]["not_have_events"]
            text = ""
            for idx, event in enumerate(events):
                changes_text = ""
                changes = event["changes"]
                if "health" in changes:
                    changes_text += f"❤️ {changes['health']:+}\n"
                if "satiety" in changes:
                    changes_text += f"🍎 {changes['satiety']:+}\n"
                if "happiness" in changes:
                    changes_text += f"😃 {changes['happiness']:+}\n"
                if "sleep" in changes:
                    changes_text += f"🌙 {changes['sleep']:+}\n"
                if "found" in changes:
                    for found in changes["found"]:
                        for key, value in found.items():
                            changes_text += f"+ {key}[{value}]\n"

                text += messages["interfaces"]["back_home"]["event_text"].format(
                    idx + 1, f"{event['description']}\n{changes_text}"
                )
            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]


async def get_journey_info(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            events = data.get("events")
            if events is None or events == []:
                return True, messages["errors"]["not_have_events"]
            text = events[-1]["description"]

            words = re.findall(r"\w+", text)

            replaced_words = words[:]

            # Заменить случайные слова на ##
            words_to_replace = len(words) // config["journey"]["words_to_replace"]

            # Заменить случайные слова
            indices_to_replace = random.sample(range(len(words)), words_to_replace)
            for i in indices_to_replace:
                replaced_words[i] = config["journey"]["replace_to"]

            # Собрать текст из замененных слов
            text = " ".join(replaced_words)

            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]


async def start_journey_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            if input.isdigit():
                data["journey_duration"] = int(input)
                data["events"] = []
                pet.data = str(data)
                await session.commit()
                status, text = await start_journey(pet.id)
                if status:
                    return True, ""
                else:
                    return False, text
            else:
                return False, messages["errors"]["not_int"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def back_home_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                if pet.state == "traveling":
                    pet.state = "nothing"
                    await session.commit()
                    status, text = await finally_journey(user_id)
                    if status:
                        return True, text
                    else:
                        return False, text
                else:
                    return False, messages["errors"]["not_traveling"]
            else:
                return False, messages["errors"]["dead"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def open_actions(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.status == "live":
                return True, ""
            else:
                return False, messages["errors"]["dead"]
        else:
            return False, messages["errors"]["not_have_pet"]
