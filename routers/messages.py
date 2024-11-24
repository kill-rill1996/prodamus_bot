from database.schemas import UserRel
from routers.utils import convert_date


def get_status_message(user_with_sub: UserRel) -> str:
    """Status message"""
    subscription = user_with_sub.subscription[0]
    if subscription.active:
        message = "✅ Ваша подписка активна\n\n"
        expire_date = convert_date(subscription.expire_date)
        message += f"Срок следующего списания <b>{expire_date}</b>\n" \
                   f"Для отмены подписки нажмите кнопку отменить"

    else:
        message = "❌ Ваша подписка неактивна"

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