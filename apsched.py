import aiogram
from aiogram.exceptions import TelegramBadRequest
from database.orm import AsyncOrm
from services.channel import kick_user_from_channel


async def run_every_day(bot: aiogram.Bot) -> None:
    """Выполняется каждый день"""
    await kick_users_with_not_active_sub(bot)


async def kick_users_with_not_active_sub(bot: aiogram.Bot) -> None:
    """Выгоняем из канала пользователей, у которых неактивная подписка"""
    users = await AsyncOrm.get_all_users()

    for user in users:
        subscription = await AsyncOrm.get_subscription_by_user_id(user.id)
        if subscription.active is False:
            # выгоняем из канала
            try:
                await kick_user_from_channel(int(user.tg_id), bot)
            except Exception as e:
                print(e)

            # уведомляем пользователя
            try:
                msg = f"Вы удалены из канала"
                await bot.send_message(user.tg_id, msg)
            except TelegramBadRequest:
                pass

