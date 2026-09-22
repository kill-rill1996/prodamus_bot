import os
from datetime import timedelta, datetime

from fastapi import FastAPI, Request
from starlette import status

from settings import settings
from logger import logger

from orm import AsyncOrm
from messages import send_error_message_to_user, send_invite_link_to_user, generate_invite_link, \
    send_auto_pay_error_message_to_user, send_success_message_to_user, delete_user_from_channel, buy_subscription_error, \
    send_error_message_to_admin
from services import get_body_params_pay_success, get_body_params_auto_pay
from webhook_delivery import process_once

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


# ПОКУПКА ПОДПИСКИ
@app.post("/success_pay", status_code=status.HTTP_200_OK)
async def buy_subscription(request: Request):
    return await process_once(request, "purchase", handle_purchase)


async def handle_purchase(request: Request):
    response = await get_body_params_pay_success(request)

    if response.payment_status != "success":
        await buy_subscription_error(int(response.tg_id))
        return

    # Signature was checked before any business operations.
    if response.payment_status == "success":
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # обновляем телефон
        await AsyncOrm.update_user_phone(user.id, response.customer_phone)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(
            subscription_id=user.subscription[0].id,
            start_date=response.date_last_payment,
            expire_date=response.date_next_payment + timedelta(days=1, hours=1),    # запас по времени 1 день и 1 час
            profile_id=response.profile_id,
            trial_used=True
        )

        # генерируем ссылку на вступление в группу
        invite_link = await generate_invite_link(user)

        try:
            await send_invite_link_to_user(
                int(user.tg_id),
                invite_link,
                expire_date=response.date_next_payment,
                is_trial=response.is_trial
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {response.tg_id} после "
                         f"успешной покупки подписки (is_trial={response.is_trial}): {e}")

        # учет операции
        await AsyncOrm.add_operation(user.tg_id, "BUY_SUB", response.date_last_payment)
        logger.info(f"Пользователь с tg id {user.tg_id}, телефон {response.customer_phone} купил подписку")


# АВТОПЛАТЕЖ ПО ПОДПИСКЕ
@app.post("/auto_pay", status_code=status.HTTP_200_OK)
async def auto_pay_subscription(request: Request):
    return await process_once(request, "auto", handle_auto_payment)


async def handle_auto_payment(request: Request):
    """Прием автоплатежа по подписке"""
    response = await get_body_params_auto_pay(request)

    # Invalid signatures have already been rejected, without side effects.
    if response.error:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)
        logger.error("Prodamus reported an unsuccessful recurring payment")

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
            profile_id=response.profile_id,
            trial_used=True
        )
        try:
            await send_success_message_to_user(int(response.tg_id), response.date_next_payment)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {response.tg_id} после "
                         f"успешного продления: {e}")

        # учет операции
        await AsyncOrm.add_operation(user.tg_id, "AUTO_PAY", response.date_last_payment)
        logger.info(f"Пользователь с tg id {user.tg_id}, телефон {user.phone} автоматически оплатил подписку")
