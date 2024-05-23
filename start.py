import asyncio

from core import init_models
from core.bot import bot
from core.engine import pet_tasks


async def start():
    await init_models()

    pet_task = asyncio.create_task(pet_tasks())
    await asyncio.gather(bot.polling(), pet_task)


if __name__ == "__main__":
    asyncio.run(start())
