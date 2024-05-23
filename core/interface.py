from core import config, messages, morph
from core.database import AsyncSessionLocal, Pet, States, new_user, db
from core.utils import generate_markup, create_info_image
from core.engine import new_pet, save_pet_name, save_random_pet_name, start_play, break_play, get_age, start_sleep, break_sleep, feed


async def check_triggers(user_id, text):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(States).filter(States.user_id == user_id))
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
    name = messages["interfaces"][interface_name]["name"]
    text = messages["interfaces"][interface_name]["text"]
    img = messages["interfaces"][interface_name]["img"]
    markup = messages["interfaces"][interface_name]["buttons"]
    func = messages["interfaces"][interface_name]["func"]
    
    if not "https://" in img or "http://" in img or "/" in img or "." in img and img != "None":
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
                name = ""
                text = func_text

    if type(markup) is not list:
        markup_func = globals().get(markup)
        if markup_func:
            markup = await markup_func(user_id=user_id)
    else:
        markup = await generate_markup(markup)
    
    return name, text, img, markup

async def parse_actions(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            buttons = messages['buttons']['actions_buttons'][pet.state]
            markup = await generate_markup(buttons)
            return markup

async def parse_games(user_id):
    games = config['games']['list']
    game_names_list = [games[game]['name'] for game in games]
    markup = await generate_markup(game_names_list)
    return markup

async def parse_food(user_id):
    foods = config['food']['list']
    food_names_list = [foods[food]['name'] for food in foods]
    markup = await generate_markup(food_names_list)
    return markup

async def format_pet_info(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            text = messages['interfaces']['main_menu']['text']
            age = await get_age(pet.id)
            age_time_name = messages['time_names'][age[1]]
            agreed_word = morph.parse(age_time_name)[0]
            agreed_word = agreed_word.make_agree_with_number(age[0]).word
            text = text.format(pet.name, messages['states'][pet.state], pet.satiety, pet.happiness, pet.health, pet.sleep, messages['statuses'][pet.status], f"{age[0]} {agreed_word}")
            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]

async def start_sleep_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            await start_sleep(pet.id)
            return True, ""
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
            for name, data in config["games"]['list'].items():
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

async def feed_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            for name, data in config["food"]['list'].items():
                if input in data["name"]:
                    status, text = await feed(pet.id, input)
                    if status:
                        return True, ""
                    else:
                        return False, text
            else:
                return False, messages["errors"]["food_not_found"]
        else:
            return False, messages["errors"]["not_have_pet"]