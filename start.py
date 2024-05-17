import asyncio

from core.bot import bot


async def start():
    await asyncio.gather(bot.polling())


if __name__ == "__main__":
    asyncio.run(start())
