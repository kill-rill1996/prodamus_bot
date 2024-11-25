import aiogram
from aiogram import Router, types, Bot
from aiogram.filters import Command
from sqlalchemy.exc import IntegrityError

from database.orm import AsyncOrm
from database.schemas import UserAdd
from routers import messages as ms
from routers import keyboards as kb
from services.channel import generate_invite_link, kick_user_from_channel

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
        msg += "\n\nВы можете проверить статус подписки с помощью команды /status"
        await message.answer(msg)

    # регистрация
    else:
        # создание пользователя
        new_user = UserAdd(
            tg_id=str(message.from_user.id),
            username=message.from_user.username,
            firstname=message.from_user.first_name,
            lastname=message.from_user.last_name
        )
        user_id = await AsyncOrm.create_user(new_user)

        # создание неактивной подписки
        await AsyncOrm.create_subscription(user_id)
        msg += "\n\nНажмите кнопку ниже для оформления подписки"
        await message.answer(msg, reply_markup=kb.subscription_keyboard(is_active=False).as_markup())


@router.message(Command("status"))
async def start_handler(message: types.Message) -> None:
    """Проверка статуса подписки"""
    tg_id = str(message.from_user.id)
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    is_active = user_with_sub.subscription[0].active
    expire_date = user_with_sub.subscription[0].expire_date

    msg = ms.get_status_message(is_active, expire_date)
    await message.answer(msg, reply_markup=kb.subscription_keyboard(is_active).as_markup())


@router.callback_query(lambda c: c.data == "cancel_subscription")
async def cancel_subscription_handler(callback: types.CallbackQuery, bot: aiogram.Bot) -> None:
    """Отмена подписки"""
    tg_id = str(callback.from_user.id)

    # получение подписки
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    subscription_id = user_with_sub.subscription[0].id

    # отмена подписки
    await AsyncOrm.update_cancel_subscribe(subscription_id)
    # TODO запрос в API Prodamus
    # TODO TRY
    # TODO не кикать?
    await kick_user_from_channel(int(tg_id), bot)

    msg = ms.get_cancel_subscribe_message()
    await callback.message.edit_text(msg)


@router.callback_query(lambda c: c.data == "subscribe")
async def create_subscription_handler(callback: types.CallbackQuery, bot: aiogram.Bot) -> None:
    """Оформление подписки"""
    tg_id = str(callback.from_user.id)

    # получение подписки
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    subscription_id = user_with_sub.subscription[0].id

    # оформление подписки
    await AsyncOrm.update_subscribe(subscription_id)

    name = callback.message.from_user.username if callback.message.from_user.username else callback.message.from_user.first_name
    invite_link = await generate_invite_link(bot, name)
    await callback.message.edit_text("Подписка оформлена\n\n"
                                  "<b>Ссылка на вступление в канал активна 1 день и может быть использована только 1 раз</b>",
                                  reply_markup=kb.invite_link_keyboard(invite_link).as_markup())


@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    """Help message"""
    msg = ms.get_help_message()
    await message.answer(msg)
