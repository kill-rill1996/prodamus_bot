import json
import os
from datetime import datetime, timedelta

import pytz
from fastapi import FastAPI, Request
from prodamuspy import ProdamusPy
import requests
from starlette import status
from loguru import logger

from orm import AsyncOrm
from settings import settings
from schemas import User, UserRel, ResponseResultPayment, ResponseResultAutoPay

app = FastAPI()

log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

logger.remove()
logger.add(f"{log_folder}/fastapi.log", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}")
logger.add(f"{log_folder}/fastapi_error.log", level="ERROR", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}")


@app.get("/")
async def root():
    return {"message": "some message"}


# ПОКУПКА ПОДПИСКИ
@app.post("/success_pay", status_code=status.HTTP_200_OK)
async def body(request: Request):
    response = await get_body_params_pay_success(request)

    # проверка на успешный платеж
    if not(response.sing_is_good and response.payment_status == "success"):
        await send_error_message_to_user(int(response.tg_id))
        logger.error(f"Не прошла покупка подписки у пользователя с tg id {response.tg_id}")

    # успешная оплата
    else:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # обновляем телефон
        await AsyncOrm.update_user_phone(user.id, response.customer_phone)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(user.id,
                                        response.date_last_payment,
                                        response.date_next_payment + timedelta(days=1, hours=1))  # запас по вермени 1 день и 1 час

        # новая подписка
        invite_link = await generate_invite_link(user)
        await send_invite_link_to_user(int(user.tg_id), invite_link, expire_date=response.date_next_payment)
        logger.info(f"Пользователь с tg id {user.tg_id}, телефон {user.phone} оплатил подписку")


# АВТОПЛАТЕЖ ПО ПОДПИСКЕ
@app.post("/auto_pay", status_code=status.HTTP_200_OK)
async def auto_pay_subscription(request: Request):
    """Прием автоплатежа по подписке"""
    response = await get_body_params_auto_pay(request)

    # проверка на успешный платеж
    if not response.sing_is_good or response.error:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        if not response.sing_is_good:
            logger.error(f"Автоматический платеж не прошел у пользователя с tg id {response.tg_id} | "
                           f"ошибка проверки подписи")
        else:
            logger.error(f"Автоматический платеж не прошел у пользователя с tg id {response.tg_id} | "
                           f"prodamus error: {response.error}")
        await send_auto_pay_error_message_to_user(user)

    else:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(
            user.subscription[0].id,
            response.date_last_payment,
            response.date_next_payment + timedelta(days=1, hours=1)  # запас по времени 1 день и 1 час
        )

        await send_success_message_to_user(int(response.tg_id), response.date_next_payment)
        logger.info(f"Пользователь с tg id {user.tg_id}, телефон {user.phone} автоматически оплатил подписку")


async def generate_invite_link(user: User) -> str:
    """Создание ссылка для вступления в канал"""
    expire_date = datetime.now(tz=pytz.timezone('Europe/Moscow')) + timedelta(days=1)
    name = user.username if user.username else user.firstname
    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "createChatInviteLink"),
        data={
            "chat_id": settings.channel_id,
            "name": name,
            "expire_date": int(expire_date.timestamp()),
            "member_limit": 1,
        }
    )
    invite_link = response.json()["result"]["invite_link"]

    return invite_link


async def send_invite_link_to_user(chat_id: int, link: str, expire_date: datetime) -> None:
    """Отправка сообщения пользователю после оплаты"""
    text = "Статус подписки на закрытый канал с ежедневным питанием от Шевы:\n\n" \
           f"✅ <b>Активна</b>\n\nСледующее списание - <b>{expire_date.date().strftime('%d.%m.%Y')}</b>\n" \
           "<i>*Вы всегда можете отменить подписку через меню бота</i>\n\n" \
           "Ваша ссылка на вступление в закрытый канал\n\n" \
           "↓↓↓"

    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'text': text,
              'parse_mode': "HTML",
              "reply_markup": json.dumps(
                  {"inline_keyboard": [
                      [{"text": "🔗Вступить в канал", "url": link}],
                      [{"text": "Вернуться в меню", "callback_data": "main_menu"}]

                  ]},
                  separators=(',', ':'))
              }
    ).json()


async def send_error_message_to_user(chat_id: int) -> None:
    """Оповещение о неуспешной оплате"""
    text = "⛔️ Мы не смогли продлить вашу подписку на канал.\n\n Доступ к каналу будет прекращён.\n\n" \
           "Возможно у вас не хватает средств на балансе, либо ваша карта больше не действительна.\n\n" \
           "Попробуйте оформить подписку заново"

    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'parse_mode': "HTML",
              'text': text,
              "reply_markup": json.dumps(
                  {"inline_keyboard": [
                      [{"text": "Оформить подписку", "callback_data": "subscribe"}]
                  ]},
                  separators=(',', ':'))
              }
    ).json()


async def send_auto_pay_error_message_to_user(user: UserRel) -> None:
    """Оповещение о неуспешной периодической оплате"""
    sub_expire_date_phrase = datetime.strftime(user.subscription[0].expire_date - timedelta(days=1, hours=1), '%d.%m в %H:%M')
    date_next_payment_phare = datetime.strftime(user.subscription[0].expire_date - timedelta(hours=2), '%d.%m %H:%M')

    msg = f"⚠️ Ваш доступ к каналу скоро пропадёт\n\n" \
          f"Ваша подписка истекла {sub_expire_date_phrase} (МСК), однако списание с вашей карты не удалось." \
          f"Чтобы избежать отключения из канала, пополните баланс до {date_next_payment_phare} (МСК).\n\n" \
          f"Если оплата не будет произведена во второй раз, наша система автоматически исключит вас " \
          f"и доступ к каналу будет закрыт."

    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={
            # 'chat_id': user.tg_id,
            'chat_id': settings.admins[0],
            'text': msg,
        }
    ).json()


async def send_success_message_to_user(chat_id: int, expire_date: datetime) -> None:
    """Оповещение об успешной оплате"""
    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'parse_mode': "HTML",
              'text': f'Ваша подписка успешно продлена до <b>{expire_date.date().strftime("%d.%m.%Y")}</b>',
              }
    ).json()


async def get_body_params_pay_success(request: Request) -> ResponseResultPayment:
    """Для приема body у покупки подписки"""
    prodamus = ProdamusPy(settings.pay_token)

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())

    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])

    result = ResponseResultPayment(
        tg_id=bodyDict["order_num"],
        payment_status=bodyDict["payment_status"],
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S')    # '2024-12-26 22:08:59'
    )

    return result


async def get_body_params_auto_pay(request: Request) -> ResponseResultAutoPay:
    """Для приема body у автопродления подписки"""
    prodamus = ProdamusPy(settings.pay_token)

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())

    # логирование request body
    if "error_code" in bodyDict["subscription"]:
        log_message = ""
        for k, v in bodyDict.items():
            log_message += f"{k}: {v}\n"
        logger.error(log_message)

    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])

    result = ResponseResultAutoPay(
        tg_id=bodyDict["order_num"],
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S'),  # '2024-12-26 22:08:59'
        action_code=None,
        error_code=None,
        error=None
    )

    # успешный платеж
    if "action_code" in bodyDict["subscription"]:
        try:
            result.action_code = bodyDict["subscription"]["action_code"]
        except Exception as e:
            logger.error(f"Ошибка при обработке успешного рекуррентного платежа:\n\n{e}")

    # ошибка при платеже
    if "error_code" in bodyDict["subscription"]:
        try:
            result.error_code = bodyDict["subscription"]["error_code"]
            result.error = bodyDict["subscription"]["error"]
        except Exception as e:
            logger.error(f"Ошибка при обработке НЕ успешного рекуррентного платежа:\n\n{e}")

    return result

