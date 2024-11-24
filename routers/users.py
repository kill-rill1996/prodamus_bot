from aiogram import Router, types, Bot
from aiogram.filters import Command
from sqlalchemy.exc import IntegrityError

from database.orm import AsyncOrm
from database.schemas import UserAdd

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Старт бота и регистрация пользователя"""
    # создание пользователя
    new_user = UserAdd(
        tg_id=str(message.from_user.id),
        username=message.from_user.username,
        firstname=message.from_user.first_name,
        lastname=message.from_user.last_name
    )

    # регистрация
    try:
        user_id = await AsyncOrm.create_user(new_user)

        # создание неактивной подписки
        await AsyncOrm.create_subscription(user_id)

        await message.answer("Успешная регистрация")

    # уже зарегистрирован
    except IntegrityError:
        await message.answer("Вы уже зарегистрированы")
