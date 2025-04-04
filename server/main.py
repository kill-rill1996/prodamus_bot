import os
from datetime import timedelta, datetime

from fastapi import FastAPI, Request
from starlette import status

from settings import settings
from logger import logger

from orm import AsyncOrm
from messages import send_error_message_to_user, send_invite_link_to_user, generate_invite_link, \
    send_auto_pay_error_message_to_user, send_success_message_to_user, delete_user_from_channel, buy_subscription_error
from services import get_body_params_pay_success, get_body_params_auto_pay

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


# ПОКУПКА ПОДПИСКИ
@app.post("/success_pay", status_code=status.HTTP_200_OK)
async def buy_subscription(request: Request):
    response = await get_body_params_pay_success(request)

    # проверка на успешный платеж
    if not(response.sing_is_good and response.payment_status == "success"):
        await buy_subscription_error(int(response.tg_id))
        logger.error(f"Не прошла покупка подписки у пользователя с tg id {response.tg_id}")

    # успешная оплата
    else:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # обновляем телефон
        await AsyncOrm.update_user_phone(user.id, response.customer_phone)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(
            subscription_id=user.subscription[0].id,
            start_date=response.date_last_payment,
            expire_date=response.date_next_payment + timedelta(days=1, hours=1),    # запас по времени 1 день и 1 час
            profile_id=response.profile_id
        )

        # новая подписка
        invite_link = await generate_invite_link(user)
        await send_invite_link_to_user(int(user.tg_id), invite_link, expire_date=response.date_next_payment)

        # учет операции
        await AsyncOrm.add_operation(user.tg_id, "BUY_SUB", response.date_last_payment)
        logger.info(f"Пользователь с tg id {user.tg_id}, телефон {response.customer_phone} купил подписку")


# АВТОПЛАТЕЖ ПО ПОДПИСКЕ
@app.post("/auto_pay", status_code=status.HTTP_200_OK)
async def auto_pay_subscription(request: Request):
    """Прием автоплатежа по подписке"""
    response = await get_body_params_auto_pay(request)

    # неуспешные автоплатежи
    if not response.sing_is_good or response.error:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        if not response.sing_is_good:
            logger.error(f"Автоплатеж не прошел tg_id {response.tg_id} | ошибка проверки подписи")
        else:
            logger.error(f"Автоплатеж платеж не прошел tg id {response.tg_id} | prodamus error: {response.error}")

        # оповещаем пользователя при первой неудачной попытке списания
        if response.current_attempt == "1" and response.action_type == "notification":
            await send_auto_pay_error_message_to_user(user)

        # при последней неудачной попытке списания и отмене подписки в продамусе
        if response.last_attempt == "yes" and response.action_code == "deactivation":
            # деактивируем подписку
            await AsyncOrm.deactivate_subscription(user.id)

            # кикаем из канала
            await delete_user_from_channel(settings.channel_id, int(user.tg_id))

            # оповещаем пользователя, что подписка кончилась
            await send_error_message_to_user(int(user.tg_id))

            # учитываем отмену подписки
            await AsyncOrm.add_operation(user.tg_id, "AUTO_UN_SUB", datetime.now())

    # успешные автоплатежи
    elif response.action_type == "action" and response.action_code == "auto_payment":
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(
            subscription_id=user.subscription[0].id,
            start_date=response.date_last_payment,
            expire_date=response.date_next_payment + timedelta(days=1, hours=1),  # запас по времени 1 день и 1 час
            profile_id=response.profile_id
        )
        await send_success_message_to_user(int(response.tg_id), response.date_next_payment)

        # учет операции
        await AsyncOrm.add_operation(user.tg_id, "AUTO_PAY", response.date_last_payment)
        logger.info(f"Пользователь с tg id {user.tg_id}, телефон {user.phone} автоматически оплатил подписку")
