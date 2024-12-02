import json
from datetime import datetime, timedelta

import pytz
from fastapi import FastAPI, Request
from prodamuspy import ProdamusPy
import requests

from orm import AsyncOrm
from settings import settings
from schemas import UserRel, User

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


@app.post("/success_pay")
async def body(request: Request):
    request_params = await get_body_params(request)
    user = await AsyncOrm.get_user_by_tg_id(request_params["order_num"])

    await AsyncOrm.create_payment(user.id)
    await AsyncOrm.update_subscribe(user.id)

    invite_link = await generate_invite_link(user)
    await send_message_to_user(int(user.tg_id), invite_link)


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


async def send_message_to_user(chat_id: int, link: str) -> None:
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


async def get_body_params(request: Request) -> dict:
    prodamus = ProdamusPy(settings.pay_token)

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())
    print(f"DECODED BODY: {bodyDict}")

    # TODO доделать проверку и не возвращать если подделка
    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])
    print(signIsGood)

    result = {
        "order_num": bodyDict["order_num"],  # tg_id: str
        "payment_status": bodyDict["payment_status"],
        "sing_is_good": signIsGood,  # bool
    }

    print(result)

    return result