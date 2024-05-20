from core import config, messages
from core.database import Session, Pet, States, new_user
from core.utils import generate_markup
from core.engine import new_pet, save_pet_name, save_random_pet_name


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
    markdown = await generate_markup(messages["interfaces"][interface_name]["buttons"])
    func = messages["interfaces"][interface_name]["func"]
    next_func = messages["interfaces"][interface_name].get("next_func")
    
    if next_func is None:
        next_func = "Nones"
    
    if func != "None" and next_func != "None":
        if input:
            function_to_call = globals().get(next_func)
        else:
            function_to_call = globals().get(func)
        if function_to_call:
            if not input:
                status, func_text = await function_to_call(user_id=user_id)
            else:
                status, func_text = await function_to_call(user_id=user_id, input=input)

        if status:
            if func_text is not None and func_text != "" and func_text != "None":
                text = func_text

    return name, text, img, markdown
