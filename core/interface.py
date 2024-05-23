from core import config, messages, morph
from core.database import AsyncSessionLocal, Pet, States, new_user, db, get_data, get_inventory
from core.utils import generate_markup, create_info_image
from core.engine import new_pet, save_pet_name, save_random_pet_name, start_play, break_play, get_age, start_sleep, break_sleep, feed, start_collect_food, break_collect_food


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
    buttons_in_row = messages["interfaces"][interface_name].get('buttons_in_row')
    func = messages["interfaces"][interface_name]["func"]  
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()

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
            if buttons_in_row is not None:
                markup = await markup_func(user_id=user_id, buttons_in_row=buttons_in_row)
            else:
                markup = await markup_func(user_id=user_id)
    else:
        if buttons_in_row is not None:
            markup = await generate_markup(markup, buttons_in_row=buttons_in_row)
        else:
            markup = await generate_markup(markup)
        
    if (name == messages['errors']['not_have_pet'] or text == messages['errors']['not_have_pet']) and pet is None:
        name = messages['errors']['not_have_pet']
        text = ""
        img = "None"
        markup = await generate_markup(messages['buttons']['not_have_pet'])
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
    game_names_list.append(messages['buttons']['actions'])
    markup = await generate_markup(game_names_list)
    return markup

async def parse_food(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
    if pet:
        foods = await get_inventory(pet.id)
        foods = [value['name'] for key, value in foods.items() if value['class'] == 'food']
        foods.append(messages['buttons']['actions'])
        markup = await generate_markup(foods)
        return markup
    else:
        return await generate_markup(messages['buttons']['main_menu'])

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
        
        
async def start_collect_food_interface(user_id, input):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if input.isdigit():
                amount = int(input)
                if amount <= config['collect_food']['max_collect_food']:
                    status, text = await start_collect_food(pet.id, amount)
                    if status:
                        return True, ""
                    else:
                        return False, text
                else:
                    return False, messages["errors"]["too_much_food_for_collect"].format(config['collect_food']['max_collect_food'])
            else:
                return False, messages["errors"]["not_int"]
        else:
            return False, messages["errors"]["not_have_pet"]
        
        
async def progress_collect_food_interface(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if pet:
            if pet.state == 'collecting':
                data = await get_data(pet.id)
                text = messages['interfaces']['progress_collect_food']['text'].format(data['collected_food'], data['required_amount_collect_food'])
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
            text = ''
            for item_name, item_data in inventory.items():
                text += messages['interfaces']['inventory']['item_text'].format(item_data['name'], item_data['amount'])
            return True, text
        else:
            return False, messages["errors"]["not_have_pet"]