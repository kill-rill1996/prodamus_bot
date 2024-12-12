from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from database.schemas import UserRel


def main_menu_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура главного меню"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Перейти в канал", url="https://t.me/+zcK6n-tCqW8zYWU6"))
    keyboard.row(InlineKeyboardButton(text="Подписка", callback_data="callback_podpiska"))
    keyboard.row(InlineKeyboardButton(text="Задать вопрос", callback_data="callback_vopros"))
    keyboard.adjust(1)

    return keyboard


def podpiska_menu_keyboard(need_back_button: bool = True) -> InlineKeyboardBuilder:
    """Клавиатура меню полпсики"""
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text="Статус моей подписки", callback_data="callback_status"))
    keyboard.row(InlineKeyboardButton(text="Отменить подписку", callback_data="callback_otmena"))
    if need_back_button:
        keyboard.row(InlineKeyboardButton(text="<< назад", callback_data="main_menu"))
    keyboard.adjust(1)

    return keyboard


def back_keyboard(callback_data: str) -> InlineKeyboardBuilder:
    """Клавиатура для возвращения назад"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="<< назад", callback_data=f"{callback_data}"))
    return keyboard


def subscription_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура продления/отмены подписки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Оформить подписку", callback_data=f"subscribe"))
    keyboard.adjust(1)

    return keyboard


def payment_keyboard(payment_link: str, need_back_button: bool = True) -> InlineKeyboardBuilder:
    """Клавиатура со ссылкой на оплату"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💵 Ссылка на оплату", url=payment_link))
    keyboard.row(InlineKeyboardButton(text="публичная оферта", url="https://www.google.ru/?hl=ru"))
    if need_back_button:
        keyboard.row(InlineKeyboardButton(text="<< назад", callback_data="back_to_start"))
    keyboard.adjust(1)

    return keyboard


def payment_keyboard_web_app(payment_link: str) -> InlineKeyboardMarkup:
    """Клавиатура со ссылкой на оплату"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="💵 Ссылка на оплату",
            web_app=WebAppInfo(url=payment_link),
        )
    ]])

    return keyboard


def yes_no_keyboard(need_back_button: bool = True) -> InlineKeyboardBuilder:
    """Подтверждение или отказ отмены подписки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Да", callback_data="yes_otmena"))
    keyboard.row(InlineKeyboardButton(text="Нет", callback_data="callback_podpiska"))

    if need_back_button:
        keyboard.row(InlineKeyboardButton(text="<< назад", callback_data="callback_podpiska"))

    keyboard.adjust(2)

    return keyboard



# def invite_link_keyboard(link: str) -> InlineKeyboardBuilder:
#     """Клавиатура со ссылкой на вступление в канал"""
#     keyboard = InlineKeyboardBuilder()
#     keyboard.row(InlineKeyboardButton(text="🔗 Вступить в канал", url=link))
#
#     return keyboard


def cancel_sub_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для отмены подписки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Отменить подписку", callback_data="cancel_subscription"))

    return keyboard