import json
from datetime import datetime, timedelta

import pytz
from fastapi import FastAPI, Request
from prodamuspy import ProdamusPy
import requests
from starlette import status

from orm import AsyncOrm
from settings import settings
from schemas import User, ResponseResult

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


@app.post("/success_pay", status_code=status.HTTP_200_OK)
async def body(request: Request):
    response = await get_body_params(request)

    # проверка на успешный платеж
    if not(response.sing_is_good and response.payment_status == "success"):
        await send_error_message_to_user(int(response.tg_id))

    # успешная оплата
    else:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)
        sub_status: bool = user.subscription[0].active

        # обновляем телефон если еще не было
        if not user.phone:
            await AsyncOrm.update_user_phone(user.id, response.customer_phone)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(user.id, response.date_last_payment, response.date_next_payment)

        # если подписка активна и продлилась
        if sub_status:
            pass

        # новая подписка
        else:
            invite_link = await generate_invite_link(user)
            await send_invite_link_to_user(int(user.tg_id), invite_link)


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
    print(invite_link)

    return invite_link


async def send_invite_link_to_user(chat_id: int, link: str) -> None:
    """Отправка сообщения пользователю после оплаты"""
    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'text': 'Ваша ссылка на вступление в закрытый канал',
              "reply_markup": json.dumps(
                  {"inline_keyboard": [[{"text": "🔗Вступить в канал", "url": link}]]},
                  separators=(',', ':'))
              }
    ).json()
    print(response)


async def send_error_message_to_user(chat_id: int) -> None:
    """Оповещение о неуспешной оплате"""
    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'text': 'Ошибка при выполнении оплаты подписки',
              }
    ).json()


async def get_body_params(request: Request) -> ResponseResult:
    prodamus = ProdamusPy(settings.pay_token)

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())
    print(f"DECODED BODY: {bodyDict}")

    # TODO доделать проверку и не возвращать если подделка
    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])
    print(signIsGood)

    result = ResponseResult(
        tg_id=bodyDict["order_num"],
        payment_status=bodyDict["payment_status"],
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S')    # '2024-12-26 22:08:59'
    )

    print(result)
    return result
