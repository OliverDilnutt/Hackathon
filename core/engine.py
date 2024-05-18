from core import config, logging, messages, bot, config_path
from core.database import Pet, Session

from datetime import datetime, timedelta
import asyncio
import yaml


async def hunger(id, auto=True, index=None):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    if auto:
        pet.satiety = pet.satiety - config['engine']['hunger_index']
    else:
        pet.satiety = pet.satiety - index
        
    session.commit()
    session.close()

    # smth edit



async def sadness(id, auto=True, index=None):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    if auto:
        pet.happiness = pet.happiness - config['engine']['sadness_index']
    else:
        pet.happiness = pet.happiness - index
        
    session.commit()
    session.close()
        
        
async def health(id, auto=True, index=None):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    if auto:
        pet.health = pet.health - config['engine']['health_index']
    else:
        pet.health = pet.health - index
        
    session.commit()
    session.close()
        

async def get_age(id):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    born = datetime.strptime(pet.born, '%Y-%m-%d %H:%M:%S.%f')
    
    age = datetime.now() - born
    
    session.close()
    
    if age.days > 0:
        return age.days, 'days'
    elif age.seconds // 3600 > 0:
        return age.seconds // 3600, 'hours'
    elif age.seconds // 60 > 0:
        return age.seconds // 60, 'minutes'
    else:
        return age.seconds, 'seconds'
    

async def die(id):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    pet.status = 'dead'
    pet.death = datetime.now()
    
    session.commit()
    session.close()
    
    
async def get_info(id):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    session.close()
    
    if pet.status == 'live':
        status = messages['state']['live']
        
    elif pet.status == 'dead':
        status = messages['state']['dead']
    
    data = {
        'id': pet.id,
        'name': pet.name,
        'satiety': pet.satiety,
        'happiness': pet.happiness,
        'health': pet.health,
        'born': pet.born,
        'age': await get_age(pet.id),
        'status': status
    }
    
    if pet.status == 'dead':
        data['death'] = pet.death
        
    return data

    
async def play(id, game):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    last_game = pet.last_game
    if last_game != game:
        pet.happiness = min(pet.happiness + config['engine']['play_index'], 100)
        
    else:
        happiness = (pet.happiness - config['engine']['play_index']) * (100 - config['engine']['play_sad_index']) // 100
        pet.happiness = min(happiness, 100)
    
    pet.state = 'playing'
    pet.last_game = game
    
    session.commit()
    session.close()
    
    
async def break_play(id):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    pet.state = 'nothing'
    pet.happiness -= config['engine']['break_play_index']
    
    session.commit()
    session.close()   
    

async def feed(id, food):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    pet.satiety = min(pet.satiety + config['engine']['foof']['feed_index'], 100)
    
    session.commit()
    session.close()
    

async def sleep(id):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    pet.health = min(pet.health + config['engine']['sleep_index'], 100)
    
    pet.state = 'sleeping'
    
    session.commit()
    session.close()
    
    
async def break_sleep(id):
    session = Session()
    
    pet = session.query(Pet).filter(Pet.id == id and Pet.status == 'live').first()
    
    pet.state = 'nothing'
    pet.happiness -= config['engine']['break_sleep_index']
    
    session.commit()
    session.close()
    

    
# Automatic updates
async def edit_pet():
    session = Session()
    
    pets = session.query(Pet).filter(Pet.status == 'live').all()
    print(pets)
    for pet in pets:
        print(pet.name)
        await hunger(pet.id)
        await sadness(pet.id)
        print(await get_age(pet.id))
    
    
async def pet_tasks():
    while True:
        time = config['engine']['time_of_last_check']
        if time != "None": 
            time = datetime.fromisoformat(time) 
            time = time + timedelta(seconds=config['engine']['pet_tasks_time']) 
            if datetime.now() >= time: 
                await edit_pet() 
                config['engine']['time_of_last_check'] = datetime.now().isoformat() 
                with open(config_path, "w") as f: 
                    yaml.dump(config, f, allow_unicode=True) 
        else: 
            config['engine']['time_of_last_check'] = datetime.now().isoformat() 
            with open(config_path, "w") as f: 
                yaml.dump(config, f, allow_unicode=True)
        
        await asyncio.sleep(config['engine']['pet_tasks_time'])