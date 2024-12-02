from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

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


def invite_link_keyboard(link: str) -> InlineKeyboardBuilder:
    """Клавиатура со ссылкой на вступление в канал"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔗 Вступить в канал", url=link))
    return keyboard
