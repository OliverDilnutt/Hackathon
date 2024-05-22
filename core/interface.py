from core import config, messages, morph
from core.database import Session, Pet, States, new_user
from core.utils import generate_markup
from core.engine import new_pet, save_pet_name, save_random_pet_name, start_play, break_play, get_age, start_sleep, break_sleep, feed


async def check_triggers(user_id, text):
    session = Session()

    state = session.query(States).filter(States.user_id == user_id).first()
    
    for interface_name, interface_data in messages["interfaces"].items():
        if text in interface_data["trigger"]:
            session.close()
            return True, False, interface_name
    else:
        if state is not None and state.state != None:
            session.close()
            return True, text, interface_name
        else:
            session.close()
            return False, False, messages["interfaces"]["not_found"]["text"]


async def show_interface(user_id, interface_name, input=False):
    name = messages["interfaces"][interface_name]["name"]
    text = messages["interfaces"][interface_name]["text"]
    img = messages["interfaces"][interface_name]["img"]
    # markup = await generate_markup(messages["interfaces"][interface_name]["buttons"])
    markup = messages["interfaces"][interface_name]["buttons"]
    func = messages["interfaces"][interface_name]["func"]
    
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
        markup_func= globals().get(markup)
        if markup_func:
            markup = await markup_func(user_id=user_id)
    else:
        markup = await generate_markup(markup)
    
    return name, text, img, markup


async def parse_actions(user_id):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    buttons = messages['buttons']['actions_buttons'][pet.state]
    markup = await generate_markup(buttons)
    return markup


async def parse_games(user_id):
    games = config['games']['list']
    game_names_list = []
    for game in games:
        game_names_list.append(games[game]['name'])
    markup = await generate_markup(game_names_list)
    return markup


async def parse_food(user_id):
    foods = config['food']['list']
    food_names_list = []
    for food in foods:
        food_names_list.append(foods[food]['name'])
    markup = await generate_markup(food_names_list)
    return markup


async def format_pet_info(user_id):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        session.close()
        text = messages['interfaces']['main_menu']['text']
        age = await get_age(pet.id)
        age_time_name = messages['time_names'][age[1]]
        agreed_word = morph.parse(age_time_name)[0]
        agreed_word = agreed_word.make_agree_with_number(age[0]).word
        text = text.format(pet.name, messages['states'][pet.state], pet.satiety, pet.happiness, pet.health, pet.sleep, messages['statuses'][pet.status], f"{age[0]} {agreed_word}")
        
        return True, text
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]
    
    
async def start_sleep_interface(user_id):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        session.close()
        await start_sleep(pet.id)
        return True, ""
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]
    
    
async def break_sleep_interface(user_id):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        session.close()
        await break_sleep(pet.id)
        return True, ""
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]
    
    
async def start_play_interface(user_id, input):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        session.close()
        for name, data in config["games"]['list'].items():
            if input in data["name"]:
                status, text = await start_play(pet.id, input)
                if status:
                    return True, ""
                else:
                    return False, text
        else:
            session.close()
            return False, messages["errors"]["game_not_found"]
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]
    
    
async def break_play_interface(user_id):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        session.close()
        await break_play(pet.id)
        return True, ""
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]
    
    
async def feed_interface(user_id, input):
    session = Session()

    pet = session.query(Pet).filter(Pet.user_id == user_id).first()
    if pet:
        session.close()
        for name, data in config["food"]['list'].items():
            if input in data["name"]:
                status, text = await feed(pet.id, input)
                if status:
                    return True, ""
                else:
                    return False, text
        else:
            session.close()
            return False, messages["errors"]["food_not_found"]
    else:
        session.close()
        return False, messages["errors"]["not_have_pet"]