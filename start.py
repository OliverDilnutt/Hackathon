import asyncio

from core.bot import bot
from core.engine import pet_tasks


async def start():
    pet_task = asyncio.create_task(pet_tasks())
    await asyncio.gather(bot.polling(), pet_task)


if __name__ == "__main__":
    asyncio.run(start())
