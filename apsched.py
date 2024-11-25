import datetime

import aiogram

from database import tables
from settings import settings


def is_sub_expire(user: tables.User) -> bool:
    """Проверка истечения срока подписки"""
    if user.subscription[0].expire_date.date() < datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")).date():
        return True
    return False


async def kick_user_from_channel(user_tg_id: int, bot: aiogram.Bot):
    """Удаление пользователя из канала"""
    await bot.ban_chat_member(settings.channel_id, user_tg_id)
    await bot.unban_chat_member(settings.channel_id, user_tg_id)


async def notify_user_about_expiration(user_tg_id: int, bot: aiogram.Bot):
    """Оповещение пользователя об окончании подписки"""
    await bot.send_message(user_tg_id, "⚠️ Ваша подписка закончилась\n\n"
                                       "Вы можете приобрести подписку с помощью команды /status")