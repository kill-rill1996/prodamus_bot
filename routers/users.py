from asyncio import sleep

import aiogram
from aiogram import Router, types, Bot
from aiogram.filters import Command
from sqlalchemy.exc import IntegrityError

from database.orm import AsyncOrm
from database.schemas import UserAdd
from routers import messages as ms
from routers import keyboards as kb
from services import prodamus
from services.channel import kick_user_from_channel

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Старт бота и регистрация пользователя"""
    # проверка наличия пользователя
    tg_id = str(message.from_user.id)
    user = await AsyncOrm.get_user_by_tg_id(tg_id)
    msg = ms.get_welcome_message()

    # уже зарегистрирован
    if user:
        user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
        if user_with_sub.subscription[0].active:
            msg += "\n\nВы можете проверить статус подписки с помощью команды /status"
            await message.answer(msg)
        else:
            msg += "\n\nНажмите кнопку ниже для оформления подписки"
            await message.answer(msg, reply_markup=kb.subscription_keyboard().as_markup())

    # регистрация
    else:
        # создание пользователя
        new_user = UserAdd(
            tg_id=str(message.from_user.id),
            username=message.from_user.username,
            firstname=message.from_user.first_name,
            lastname=message.from_user.last_name,
            # phone=None
        )
        user_id = await AsyncOrm.create_user(new_user)

        # создание неактивной подписки
        await AsyncOrm.create_subscription(user_id)
        msg += "\n\nНажмите кнопку ниже для оформления подписки"
        await message.answer(msg, reply_markup=kb.subscription_keyboard().as_markup())


@router.message(Command("status"))
async def start_handler(message: types.Message) -> None:
    """Проверка статуса подписки"""
    tg_id = str(message.from_user.id)
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    is_active = user_with_sub.subscription[0].active
    expire_date = user_with_sub.subscription[0].expire_date

    msg = ms.get_status_message(is_active, expire_date)

    if not is_active:
        await message.answer(msg, reply_markup=kb.subscription_keyboard().as_markup())
    else:
        await message.answer(msg)


@router.callback_query(lambda c: c.data == "subscribe")
async def create_subscription_handler(callback: types.CallbackQuery) -> None:
    """Оформление подписки"""
    payment_link = prodamus.get_pay_link(callback.from_user.id)

    await callback.message.edit_text(
        "Для оформления подписки на месяц оплатите по ссылке ниже\n\n",
        reply_markup=kb.payment_keyboard(payment_link).as_markup()
    )


@router.callback_query(lambda c: c.data == "cancel_subscription")
async def cancel_subscription_handler(callback: types.CallbackQuery) -> None:
    """Отмена подписки"""
    tg_id = str(callback.from_user.id)

    # получение подписки
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    subscription_id = user_with_sub.subscription[0].id

    # отмена подписки через API Prodamus
    status_code = prodamus.cancel_sub_by_user(user_with_sub.phone)
    if status_code == 200:
        # отмена подписки в БД
        await AsyncOrm.update_cancel_subscribe(subscription_id)

        msg = ms.get_cancel_subscribe_message()
        await callback.message.edit_text(msg)
    else:
        await callback.message.edit_text("Произошла ошибка при обработке запроса. Повторите запрос позже.")


@router.message(Command("test"))
async def cancel_sub(message: types.Message) -> None:
    """Cancel sub"""
    prodamus.cancel_sub_by_user("+79855517159")

    msg = ms.get_help_message()
    await message.answer(msg)


@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    """Help message"""
    msg = ms.get_help_message()
    await message.answer(msg)
