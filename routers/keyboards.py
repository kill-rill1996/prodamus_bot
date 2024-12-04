from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from database.schemas import UserRel


def subscription_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура продления/отмены подписки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Оформить подписку", callback_data=f"subscribe"))
    keyboard.adjust(1)

    return keyboard


def payment_keyboard(payment_link: str) -> InlineKeyboardBuilder:
    """Клавиатура со ссылкой на оплату"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💵 Ссылка на оплату", url=payment_link))

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



def invite_link_keyboard(link: str) -> InlineKeyboardBuilder:
    """Клавиатура со ссылкой на вступление в канал"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔗 Вступить в канал", url=link))

    return keyboard


def cancel_sub_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура для отмены подписки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Отменить подписку", callback_data="cancel_subscription"))

    return keyboard