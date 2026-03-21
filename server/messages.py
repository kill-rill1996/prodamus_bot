import json
from datetime import datetime, timedelta

import pytz
import requests

from schemas import User, UserRel
from settings import settings
from logger import logger


PROXIES = {
    "http": f"socks5h://{settings.proxy_ip}:{settings.proxy_port}",
    "https": f"socks5h://{settings.proxy_ip}:{settings.proxy_port}",
}

# Создаём сессию один раз
session = requests.Session()
session.proxies.update(PROXIES)

async def generate_invite_link(user: User) -> str:
    """Создание ссылка для вступления в канал"""
    expire_date = datetime.now(tz=pytz.timezone('Europe/Moscow')) + timedelta(days=1)
    name = user.username if user.username else user.firstname
    response = session.post(
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


async def send_invite_link_to_user(chat_id: int, link: str, expire_date: datetime, is_trial: bool = False) -> None:
    """Отправка сообщения пользователю после оплаты"""
    text = "Статус подписки на закрытый канал с ежедневным питанием от Шевы:\n\n" \
           f"✅ <b>Активна</b> {f'(активирован пробный период на <b>{settings.trial_period}</b> дня)' if is_trial else ''}" \
           f"\n\nСледующее списание - <b>{expire_date.date().strftime('%d.%m.%Y')}</b>\n" \
           "<i>*Вы всегда можете отменить подписку через меню бота</i>\n\n" \
           "Ваша ссылка на вступление в закрытый канал\n\n" \
           "↓↓↓"

    response = session.post(
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
    """Оповещение о неуспешном автоплатеже"""
    text = "Мы не смогли продлить твою подписку на канал ⚠️\n\n<b>Доступ к каналу прекращён</b>\n\n" \
           "Возможно у тебя не хватает денег на балансе, либо карта больше не действительна. Попробуй оформить подписку заново.\n\n" \
           "Если хочешь продолжать следить за питанием с нами вместе, то жду тебя обратно в канал 🫰"

    response = session.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={
            'chat_id': chat_id,
            'parse_mode': "HTML",
            'text': text,
            "reply_markup": json.dumps(
                {"inline_keyboard": [
                    [{"text": "Оформить подписку", "callback_data": "subscribe"}]
                ]},
                separators=(',', ':'))
              }
    ).json()


async def buy_subscription_error(chat_id: int) -> None:
    """Ошибка при неуспешной покупке подписки"""
    text = "⛔️ Ошибка при оплате подписки.\n\n " \
           "Возможно у вас не хватает средств на балансе, либо ваша карта больше не действительна.\n\n" \
           "Попробуйте оформить подписку заново"

    response = session.post(
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

    msg_for_client = f"⚠️ Ваш доступ к каналу скоро пропадёт\n\n" \
          f"Ваша подписка истекает <b>{sub_expire_date_phrase} (МСК)</b>, однако списание с вашей карты не удалось." \
          f"Чтобы избежать отключения из канала, пополните баланс до <b>{date_next_payment_phare} (МСК)</b>.\n\n" \
          f"Если оплата не будет произведена во второй раз, наша система автоматически исключит вас " \
          f"и доступ к каналу будет закрыт."

    msg_for_admin = f"У пользователя tg_id: {user.tg_id}, phone: {user.phone} не удалось списать деньги 1 раз\n" \
          f"подписка истекает {sub_expire_date_phrase} (МСК)\n" \
          f"Чтобы избежать отключения из канала, пополните баланс до {date_next_payment_phare} (МСК)"

    # сообщение клиенту
    response = session.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={
            'chat_id': user.tg_id,
            'parse_mode': "HTML",
            'text': msg_for_client,
        }
    ).json()

    # сообщение админу
    response = session.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={
            # TODO тестовый chat_id
            # 'chat_id': user.tg_id,
            'chat_id': settings.admins[0],
            'parse_mode': "HTML",
            'text': msg_for_admin,
        }
    ).json()


async def send_success_message_to_user(chat_id: int, expire_date: datetime) -> None:
    """Оповещение об успешной оплате"""
    response = session.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
        data={'chat_id': chat_id,
              'parse_mode': "HTML",
              'text': f'Ваша подписка успешно продлена до <b>{expire_date.date().strftime("%d.%m.%Y")}</b>',
              }
    ).json()


async def delete_user_from_channel(channel_id: int, user_id: int) -> None:
    """Кик пользователя из канала"""
    logger.info(f"Идет удаление пользователя из канала")

    response = session.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "banChatMember"),
        data={
            'chat_id': channel_id,
            'user_id': user_id,
        }
    ).json()

    _ = session.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "unbanChatMember"),
        data={
            'chat_id': channel_id,
            'user_id': user_id,
        }
    ).json()

    logger.info(f"Пользователь tg_id {user_id} удален из канала")


async def send_error_message_to_admin(buy_type: str, response) -> None:
    """Отправка сообщения о неудачном платеже администратору"""
    msg = f"⛔️ Ошибка проверки подписи при оплате подписки\nТип покупки: <b>{buy_type}</b>\n\nRESPONSE\n{response}"

    for chat_id in [420551454, 714371204]:
        response = session.post(
            url='https://api.telegram.org/bot{0}/{1}'.format(settings.bot_token, "sendMessage"),
            data={'chat_id': chat_id,
                  'parse_mode': "HTML",
                  'text': msg,
                  }
        ).json()