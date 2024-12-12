import json
from datetime import datetime, timedelta

import pytz
from fastapi import FastAPI, Request
from prodamuspy import ProdamusPy
import requests
from starlette import status

from orm import AsyncOrm
from settings import settings
from schemas import User, ResponseResultPayment, ResponseResultAutoPay

app = FastAPI()


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

    # успешная оплата
    else:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # обновляем телефон
        await AsyncOrm.update_user_phone(user.id, response.customer_phone)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(user.id,
                                        response.date_last_payment,
                                        response.date_next_payment + timedelta(days=1)  # запас по вермени 1 день
        )

        # новая подписка
        invite_link = await generate_invite_link(user)
        await send_invite_link_to_user(int(user.tg_id), invite_link, expire_date=response.date_next_payment)


# АВТОПЛАТЕЖ ПО ПОДПИСКЕ
@app.post("/auto_pay", status_code=status.HTTP_200_OK)
async def auto_pay_subscription(request: Request):
    """Прием автоплатежа по подписке"""
    response = await get_body_params_auto_pay(request)

    # проверка на успешный платеж
    if not (response.sing_is_good and response.action_code == "auto_payment"):
        await send_auto_pay_error_message_to_user(int(response.tg_id))

    else:
        user = await AsyncOrm.get_user_with_subscription_by_tg_id(response.tg_id)

        # меняем дату окончания подписки
        await AsyncOrm.update_subscribe(
            user.subscription[0].id,
            response.date_last_payment,
            response.date_next_payment + timedelta(days=1)  # запас по времени 1 день
        )

        await send_success_message_to_user(int(response.tg_id), response.date_next_payment)


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
    print(response)


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


async def send_auto_pay_error_message_to_user(chat_id: int) -> None:
    """Оповещение о неуспешной периодической оплате"""
    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'text': 'Ошибка при выполнении периодического платежа по подписке',
              }
    ).json()


async def send_success_message_to_user(chat_id: int, expire_date: datetime) -> None:
    """Оповещение об успешной оплате"""
    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'text': f'Ваша подписка успешно продлена до {expire_date}',
              }
    ).json()
    print(response)


async def get_body_params_pay_success(request: Request) -> ResponseResultPayment:
    """Для приема body у покупки подписки"""
    prodamus = ProdamusPy(settings.pay_token)

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())
    print(f"DECODED BODY: {bodyDict}")

    # TODO доделать проверку и не возвращать если подделка
    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])
    print(signIsGood)

    result = ResponseResultPayment(
        tg_id=bodyDict["order_num"],
        payment_status=bodyDict["payment_status"],
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S')    # '2024-12-26 22:08:59'
    )

    print(result)
    return result


async def get_body_params_auto_pay(request: Request) -> ResponseResultAutoPay:
    """Для приема body у автопродления подписки"""
    prodamus = ProdamusPy(settings.pay_token)

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())
    print(f"DECODED BODY: {bodyDict}")

    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])
    print(signIsGood)

    result = ResponseResultAutoPay(
        tg_id=bodyDict["order_num"],
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        action_code=bodyDict["subscription"]["action_code"]
    )

    print(result)
    return result

