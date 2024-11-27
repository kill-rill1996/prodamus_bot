import asyncio
from datetime import datetime

import aiogram as io
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
# from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.database import async_engine
from database.tables import Base
from routers import users

from settings import settings


async def set_commands(bot: io.Bot):
    """Перечень команд для бота"""
    commands = [
        BotCommand(command="/start", description="Начало"),
        BotCommand(command="/status", description="Проверка подписки"),
        BotCommand(command="/help", description="Помощь"),
    ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def set_description(bot: io.Bot):
    """Описание бота до запуска"""
    await bot.set_my_description("Бот предоставляет функционал управления подписками\n\n"
                                 "Для запуска нажмите \"Начать\"")


async def start_bot() -> None:
    """Запуск бота"""
    bot = io.Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_commands(bot)
    await set_description(bot)

    storage = MemoryStorage()
    dispatcher = io.Dispatcher(storage=storage)

    # # SCHEDULER
    # scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    #
    # # оповещение для пользователей
    # scheduler.add_job(apsched.run_every_day, trigger="cron", year='*', month='*', day="*", hour=9, minute=0,
    #                   second=0, start_date=datetime.now(), kwargs={"bot": bot})
    # # проверка мероприятия на минимальное кол-во участников
    # scheduler.add_job(apsched.run_every_hour, trigger="cron", year='*', month='*', day="*", hour="*", minute="*",
    #                   second=0, start_date=datetime.now(), kwargs={"bot": bot})
    #
    # scheduler.start()

    dispatcher.include_routers(users.router)
    await init_models()

    await dispatcher.start_polling(bot)


async def init_models():
    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(start_bot())