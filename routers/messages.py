import datetime

from database.schemas import UserRel
from routers.utils import convert_date
from settings import settings


def get_welcome_message() -> str:
    """Приветственное сообщение"""
    message = f"👋 Добро пожаловать!\n\n" \
               f"💫 Этот бот управляет подпиской на закрытый канал.\n\n" \
               f"💰 Стоимость: {settings.price} руб/месяц\n" \
               f"📅 Срок подписки: 1 месяц"
    return message


def get_status_message(is_active: bool, expire_date: datetime.datetime) -> str:
    """Status message"""
    if is_active:
        message = "✅ Ваша подписка активна\n\n"
        converted_expire_date = convert_date(expire_date)
        message += f"Дата следующего списания <b>{converted_expire_date}</b>\n"

    # если подписка неактивна
    else:
        if expire_date is not None and expire_date.date() >= datetime.datetime.now().date():
            message = "⚠️ Ваша подписка отменена\n\n" \
                      f"Доступ к каналу будет прекращён {convert_date(expire_date)}.\n" \
                      f"После окончания текущей подписки, вы сможете оформить подписку заново с помощью команды /status"

        else:
            message = "❌ Ваша подписка неактивна\n\n" \
                      "Для оформления подписки нажмите кнопку \"Оформить подписку\""

    return message


def get_cancel_subscribe_message(expire_date: datetime.datetime) -> str:
    """Сообщение об отмене подписки"""
    message = "⚠️ Ваша подписка отменена\n\n" \
              f"Доступ к каналу будет прекращён {convert_date(expire_date)}.\n" \
              "Вы всегда можете оформить подписку заново с помощью команды /status"
    return message


def get_help_message() -> str:
    """Help message"""
    # TODO переделать
    message = "<b>Возможности бота:</b>\n" \
              "- Принимает оплату за подписку\n" \
              "- Осуществляет менеджмент приватных каналов/групп\n\n" \
              "<b>Инструкция использования:</b>\n" \
              "- Для проверки статуса своей подписки нажмите /status\n" \
              "- Для покупки или продления подписки в нажмите /status и кнопку оформить подписку\n\n"\
              "Бот автоматически напомнит вам о необходимости продления подписки за несколько дней до ее окончания\n\n"\
              "<b>Контакт поддержки:</b>\n" \
              f"Если у вас есть вопросы или предложения, свяжитесь с нашей поддержкой в телеграм: @aleksandr_andreew"
    return message