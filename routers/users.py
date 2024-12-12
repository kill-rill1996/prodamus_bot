import datetime

from aiogram import Router, types
from aiogram.filters import Command

from database.orm import AsyncOrm
from database.schemas import UserAdd
from routers import messages as ms
from routers import keyboards as kb
from services import prodamus

router = Router()


@router.callback_query(lambda c: c.data == "back_to_start")
@router.message(Command("start"))
async def start_handler(message: types.Message | types.CallbackQuery) -> None:
    """Старт бота и регистрация пользователя"""
    # проверка наличия пользователя
    tg_id = str(message.from_user.id)
    user = await AsyncOrm.get_user_by_tg_id(tg_id)
    msg = ms.get_welcome_message()

    # уже зарегистрирован
    if user:
        user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)

        if user_with_sub.subscription[0].active or \
                (user_with_sub.subscription[0].expire_date is not None and
                 user_with_sub.subscription[0].expire_date.date() >= datetime.datetime.now().date()):

            if type(message) == types.Message:
                await message.answer(msg)
            else:
                await message.message.edit_text(msg)
        else:
            if type(message) == types.Message:
                await message.answer(msg, reply_markup=kb.subscription_keyboard().as_markup())
            else:
                await message.message.edit_text(msg, reply_markup=kb.subscription_keyboard().as_markup())

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
        await message.answer(msg, reply_markup=kb.subscription_keyboard().as_markup())


@router.message(Command("menu"))
@router.callback_query(lambda c: c.data == "main_menu")
async def main_menu(message: types.Message | types.CallbackQuery) -> None:
    """Главное меню"""
    msg = "<b>Меню участника канала «Ежедневное питание | Sheva Nutrition»:</b>"

    if type(message) == types.Message:
        await message.answer(msg, reply_markup=kb.main_menu_keyboard().as_markup())
    else:
        await message.message.edit_text(msg, reply_markup=kb.main_menu_keyboard().as_markup())


@router.message(Command("podpiska"))
@router.callback_query(lambda c: c.data == "callback_podpiska")
async def podpiska_menu(message: types.Message | types.CallbackQuery) -> None:
    """Меню управления подпиской"""
    msg = "Своей подпиской можно управлять здесь:"

    if type(message) == types.Message:
        await message.answer(msg, reply_markup=kb.podpiska_menu_keyboard(need_back_button=False).as_markup())
    else:
        await message.message.edit_text(msg, reply_markup=kb.podpiska_menu_keyboard(need_back_button=True).as_markup())


@router.message(Command("status"))
@router.callback_query(lambda c: c.data == "callback_status")
async def start_handler(message: types.Message | types.CallbackQuery) -> None:
    """Проверка статуса подписки"""
    tg_id = str(message.from_user.id)
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)

    is_active = user_with_sub.subscription[0].active
    expire_date = user_with_sub.subscription[0].expire_date

    msg = ms.get_status_message(is_active, expire_date)

    if type(message) == types.Message:
        await message.answer(msg)
    else:
        await message.message.edit_text(msg, reply_markup=kb.back_keyboard("callback_podpiska").as_markup())


@router.message(Command("oplata"))
@router.callback_query(lambda c: c.data == "subscribe")
async def create_subscription_handler(message: types.CallbackQuery | types.Message) -> None:
    """Оформление подписки"""
    payment_link = prodamus.get_pay_link(message.from_user.id)

    # browser link
    if type(message) == types.Message:
        await message.answer(
            ms.subscribe_message(),
            reply_markup=kb.payment_keyboard(payment_link, need_back_button=False).as_markup()
        )
    else:
        await message.message.edit_text(
            ms.subscribe_message(),
            reply_markup=kb.payment_keyboard(payment_link).as_markup()
        )

    # web app
    # await callback.message.edit_text(
    #     "Для оформления подписки на месяц оплатите по ссылке ниже\n\n"
    #     "При успешной оплате ссылка на вступление в канал придет в течение 5 минут",
    #     reply_markup=kb.payment_keyboard_web_app(payment_link)
    # )


@router.message(Command("otmena"))
@router.callback_query(lambda c: c.data == "callback_otmena")
async def cancel_subscription_handler(message: types.Message | types.CallbackQuery) -> None:
    """Начало отмены подписки"""
    msg = "<b>Вы действительной хотите отменить подписку?</b>"

    if type(message) == types.Message:
        await message.answer(msg, reply_markup=kb.yes_no_keyboard(need_back_button=False).as_markup())
    else:
        await message.message.edit_text(msg, reply_markup=kb.yes_no_keyboard(need_back_button=True).as_markup())


@router.callback_query(lambda c: c.data == "yes_otmena")
async def confirmation_unsubscribe(callback: types.CallbackQuery) -> None:
    """Отмена подписки"""
    tg_id = str(callback.from_user.id)

    # получение подписки
    user_with_sub = await AsyncOrm.get_user_with_subscription_by_tg_id(tg_id)
    subscription_id = user_with_sub.subscription[0].id

    # отмена подписки через API Prodamus
    status_code = prodamus.cancel_sub_by_user(user_with_sub.phone)

    if status_code == 200:
        # отмена подписки в БД
        await AsyncOrm.disactivate_subscribe(subscription_id)

        msg = ms.get_cancel_subscribe_message(user_with_sub.subscription[0].expire_date)
        await callback.message.edit_text(msg)
    else:
        await callback.message.edit_text("Произошла ошибка при обработке запроса. Повторите запрос позже.")


@router.message(Command("vopros"))
@router.callback_query(lambda c: c.data == "callback_vopros")
async def vopros_handler(message: types.Message | types.CallbackQuery) -> None:
    """Задать вопрос"""
    msg = ms.get_vopros_message()

    if type(message) == types.Message:
        await message.answer(msg)
    else:
        await message.message.edit_text(msg, reply_markup=kb.back_keyboard("main_menu").as_markup())


# TESTING TODO потом удалить
@router.message(Command("req"))
async def req_handler(message: types.Message) -> None:
    """Help message"""
    payment_link = prodamus.get_pay_link(message.from_user.id)

    # browser link
    await message.answer(
        "Для оформления подписки на месяц оплатите по ссылке ниже\n\n"
        "При успешной оплате ссылка на вступление в канал придет в течение 5 минут",
        reply_markup=kb.payment_keyboard(payment_link).as_markup()
    )
