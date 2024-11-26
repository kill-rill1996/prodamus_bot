from aiogram import Router, types, Bot
from aiogram.filters import Command
from sqlalchemy.exc import IntegrityError

from database.orm import AsyncOrm
from database.schemas import UserAdd
from routers import messages as ms
from settings import settings
from routers import keyboards as kb
from services import prodamus

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Старт бота и регистрация пользователя"""
    # создание пользователя
    new_user = UserAdd(
        tg_id=str(message.from_user.id),
        username=message.from_user.username,
        firstname=message.from_user.first_name,
        lastname=message.from_user.last_name,
    )

    msg = ms.get_welcome_message()

    # регистрация
    try:
        user_id = await AsyncOrm.create_user(new_user)

        # создание неактивной подписки
        await AsyncOrm.create_subscription(user_id)
        msg += "\n\nНажмите кнопку ниже для оформления подписки"
        await message.answer(msg, reply_markup=kb.subscription_keyboard(is_active=False).as_markup())

    # уже зарегистрирован
    except IntegrityError:
        msg += "\n\nВы можете проверить статус подписки с помощью команды /status"
        await message.answer(msg)


@router.message(Command("status"))
async def start_handler(message: types.Message) -> None:
    """Проверка статуса подписки"""
    tg_id = str(message.from_user.id)
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    is_active = user_with_sub.subscription[0].active
    expire_date = user_with_sub.subscription[0].expire_date

    msg = ms.get_status_message(is_active, expire_date)
    await message.answer(msg, reply_markup=kb.subscription_keyboard(is_active).as_markup())


@router.callback_query(lambda c: c.data == "subscribe")
async def create_subscription_handler(callback: types.CallbackQuery) -> None:
    """Оформление подписки"""
    payment_link = prodamus.get_pay_link(callback.from_user.id)

    await callback.message.answer(
        "Для оформления подписки оплатите по ссылке ниже",
        reply_markup=
    )


@router.callback_query(lambda c: c.data == "cancel_subscription")
async def cancel_subscription_handler(callback: types.CallbackQuery) -> None:
    """Отмена подписки"""
    await callback.message.answer("Подписка отменена")


@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    """Help message"""
    msg = ms.get_help_message()
    await message.answer(msg)
