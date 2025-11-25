#точка входа 
import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
import handlers
import buttons


async def main():
    bot = Bot(token="7730230989:AAFsiiOoyRsoDb3RP9ad1GhQeK_nHqZNGs0")
    dp = Dispatcher()

    await init_db()

    dp.include_router(buttons.router)
    dp.include_router(handlers.router)

    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

