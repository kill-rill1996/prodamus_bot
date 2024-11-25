from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.schemas import UserRel


def subscription_keyboard(is_active: bool) -> InlineKeyboardBuilder:
    """Клавиатура продления/отмены подписки"""
    keyboard = InlineKeyboardBuilder()

    if is_active:
        keyboard.row(InlineKeyboardButton(text="Отменить подписку", callback_data=f"cancel_subscription"))
    else:
        keyboard.row(InlineKeyboardButton(text="Оформить подписку", callback_data=f"subscribe"))

    keyboard.adjust(1)
    return keyboard


def invite_link_keyboard(link: str) -> InlineKeyboardBuilder:
    """Клавиатура со ссылкой на вступление в канал"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔗 Вступить в канал", url=link))
    return keyboard