from datetime import datetime
from math import ceil

from core import config, messages, morph
from core.database import (
    AsyncSessionLocal,
    Pet,
    States,
    new_user,
    db,
    get_data,
    get_inventory,
)
from core.utils import generate_markup, create_info_image
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
        and interface_name not in ["start", "start_game", "hatching"]
    ):
        text = await hatching_check_interface(user_id)
        img = messages["interfaces"]["hatching_check"]["img"]
        markup = await generate_markup(
            messages["interfaces"]["hatching_check"]["buttons"]
        )
    return text, img, markup


async def parse_actions(user_id, buttons_in_row=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            buttons = messages["buttons"]["actions_buttons"][pet.state]
            markup = await generate_markup(buttons)
            return markup


async def parse_games(user_id, buttons_in_row=None):
    games = config["games"]["list"]
    game_names_list = [games[game]["name"] for game in games]
    game_names_list.append(messages["buttons"]["actions"])
    markup = await generate_markup(game_names_list)
    return markup


async def parse_food(user_id, buttons_in_row=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        foods = await get_inventory(pet.id)
        foods = [
            f"{value['name']} [{value['amount']}]"
            for key, value in foods.items()
            if value["class"] == "food"
        ]
        foods.append(messages["buttons"]["actions"])
        if buttons_in_row is not None:
            markup = await generate_markup(foods, buttons_in_row=buttons_in_row)
        else:
            markup = await generate_markup(foods)
        return markup
    else:
        return await generate_markup(messages["buttons"]["main_menu"])


async def parse_food_amount(user_id, buttons_in_row=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        food = (await get_data(pet.id))["selected_food"]
        food_amount = (await get_inventory(pet.id))[food]["amount"]
        buttons = []

        feed_index = config["food"]["list"][food]["feed_index"]
        max_amount = min(ceil((100 - pet.satiety) / int(feed_index)), food_amount)

        button_text = messages["interfaces"]["select_amount_food"]["buttons_style"]

        buttons.append(button_text.format(1, (pet.satiety + feed_index)))
        if food_amount > 1:
            buttons.append(
                button_text.format(
                    round((max_amount + 1) / 2),
                    (
                        pet.satiety
                        + (
                            round((max_amount + 1) / 2)
                            * feed_index
                        )
                    ),
                )
            )
            buttons.append(
                button_text.format(max_amount, min(pet.satiety + max_amount*feed_index, 100))
            )

        buttons.append(messages["buttons"]["actions"])
        if buttons_in_row is not None:
            markup = await generate_markup(buttons, buttons_in_row=buttons_in_row)
        else:
            markup = await generate_markup(buttons)
        return markup
    else:
        return await generate_markup(messages["buttons"]["main_menu"])


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
                return False, messages["hatching_check"]["out_of_time"]


async def hatching_check_interface(user_id):
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

                text = messages["interfaces"]["hatching_check"]["text"].format(
                    remaining_minutes,
                    agreed_word_minutes,
                    remaining_seconds,
                    agreed_word_seconds,
                )
                return True, text
            return False, messages["hatching_check"]["out_of_time"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def format_pet_info(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            text = messages["interfaces"]["main_menu"]["text"]
            age = await get_age(pet.id)
            age_time_name = messages["time_names"][age[1]]
            agreed_word = morph.parse(age_time_name)[0]
            agreed_word = agreed_word.make_agree_with_number(age[0]).word
            text = text.format(
                pet.name,
                messages["statuses"][pet.status],
                messages["states"][pet.state],
                f"{age[0]} {agreed_word}",
                pet.health,
                pet.satiety,
                pet.happiness,
                pet.sleep,
            )
            return True, text
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
                        return True, ""
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
            for name, data in config["food"]["list"].items():
                if input in data["name"]:
                    data = await get_data(pet.id)
                    data["selected_food"] = name
                    pet.data = str(data)
                    await session.commit()
                    return True, ""
            else:
                return False, messages["errors"]["food_not_found"]
        else:
            return False, messages["errors"]["not_have_pet"]


async def feed_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            data = await get_data(pet.id)
            food = data["selected_food"]
            status, text = await feed(pet.id, food, input)
            if status:
                return True, ""
            else:
                return False, text
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
            text = ""
            for item_name, item_data in inventory.items():
                text += messages["interfaces"]["inventory"]["item_text"].format(
                    item_data["name"], item_data["amount"]
                )
            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]
