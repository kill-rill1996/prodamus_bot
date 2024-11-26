import datetime

from database.schemas import UserRel
from routers.utils import convert_date
from settings import settings


def get_welcome_message() -> str:
    """Приветственное сообщение"""
    message = f"👋 Добро пожаловать!\n\n" \
               f"💫 Этот бот управляет подпиской на закрытый канал.\n\n" \
               f"💰 Стоимость: {settings.price} руб/месяц\n" \
               f"♾️ Тип подписки: Автопродление"
    return message


def get_status_message(is_active: bool, expire_date: datetime.datetime) -> str:
    """Status message"""
    if is_active:
        message = "✅ Ваша подписка активна\n\n"
        converted_expire_date = convert_date(expire_date)
        message += f"Срок следующего списания <b>{converted_expire_date}</b>\n" \
                   f"Для отмены подписки нажмите кнопку \"Отменить подписку\""

    else:
        message = "❌ Ваша подписка неактивна\n\n" \
                  "Для оформления подписки нажмите кнопку \"Оформить подписку\""

    return message


def get_cancel_subscribe_message() -> str:
    """Сообщение об отмене подписки"""
    message = "⚠️ Ваша подписка отменена\n\n" \
              "Доступ к каналу будет прекращён в течение 24 часов.\n" \
              "Вы всегда можете оформить подписку заново с помощью команды /status"
    return message


def get_help_message() -> str:
    """Help message"""
    # TODO переделать
    message = "<b>Возможности бота:</b>\n" \
              "- Принимает оплату за подписку\n" \
              "- Осуществляет менеджмент приватных каналов/групп\n\n" \
              "<b>Инструкция использования:</b>\n" \
              "- Для перехода в главное меню отправьте команду /menu\n" \
              "- Для покупки или продления подписки в главном меню нажмите \"Купить 💸\"\n" \
              "- Для проверки своего статуса подписки в главном меню нажмите \"Статус 🎫\"\n\n" \
              "<b>Контакт поддержки:</b>\n" \
              f"Если у вас есть вопросы или предложения, свяжитесь с нашей поддержкой в телеграм: @aleksandr_andreew"
    return message