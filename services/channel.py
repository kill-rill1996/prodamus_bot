from datetime import datetime, timedelta
import pytz
import aiogram
from loguru import logger

from settings import settings

logger.remove()
logger.add("logs/bot.log", format="{time:MMMM D, YYYY > HH:mm:ss} | {level} | {message} | {extra}")


async def generate_invite_link(bot: aiogram.Bot, name: str) -> str:
    """Создание ссылки для подписки на группу"""
    # время окончание действия ссылки на вступление
    expire_date = datetime.now(tz=pytz.timezone('Europe/Moscow')) + timedelta(days=1)

    invite_link = await bot.create_chat_invite_link(chat_id=settings.channel_id,
                                                    name=name,
                                                    expire_date=int(expire_date.timestamp()),
                                                    member_limit=1)
    return invite_link.invite_link


async def kick_user_from_channel(user_tg_id: int, bot: aiogram.Bot):
    """Удаление пользователя из канала"""
    await bot.ban_chat_member(settings.channel_id, user_tg_id)
    await bot.unban_chat_member(settings.channel_id, user_tg_id)
    logger.info(f"Пользователь с tg id {user_tg_id} кикнут из канала.")