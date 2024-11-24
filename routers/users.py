from aiogram import Router, types, Bot
from aiogram.filters import Command
from sqlalchemy.exc import IntegrityError

from database.orm import AsyncOrm
from database.schemas import UserAdd
from routers import messages as ms

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


@router.message(Command("status"))
async def start_handler(message: types.Message) -> None:
    """Проверка статуса подписки"""
    tg_id = str(message.from_user.id)
    user = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    msg = ms.get_status_message(user)
    await message.answer(msg)


@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    """Help message"""
    msg = ms.get_help_message()
    await message.answer(msg)
