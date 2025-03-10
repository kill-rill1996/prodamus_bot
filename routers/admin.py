import aiogram
from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from routers import keyboards as kb
from routers.fsm_states import SendMessagesFSM
from database.orm import AsyncOrm

router = Router()


@router.callback_query(lambda c: c.data == "menu_administration")
async def admin_menu(callback: types.CallbackQuery) -> None:
    """Меню администратора"""
    msg = "Панель администратора"
    await callback.message.edit_text(msg, reply_markup=kb.admin_keyboard().as_markup())


@router.callback_query(lambda c: c.data == "notify_users")
async def notify_users(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Подготовка сообщения для порльзователей"""

    await state.set_state(SendMessagesFSM.text)

    msg = "Отправьте в чат сообщение, которое вы бы хотели разослать пользователям, отменившим подписку"
    await callback.message.edit_text(msg, reply_markup=kb.cancel_keyboard().as_markup())


@router.message(SendMessagesFSM.text)
async def send_messages_to_users(message: types.Message, state: FSMContext, bot: aiogram.Bot) -> None:
    """Рассылка сообщения для пользователей"""
    await state.clear()

    msg = message.text
    operations = await AsyncOrm.get_unsub_operations()

    for operation in operations:
        try:
            await bot.send_message(operation.tg_id, msg)

        except Exception as e:
            print(f"Не удалось отправить сообщение польз. {operation.tg_id}: {e}")

    await message.answer("Пользователи оповещены")


@router.callback_query(lambda callback: callback.data == "button_cancel", StateFilter("*"))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel FSM and delete last message"""
    await state.clear()
    await callback.message.answer("<b>Действие отменено</b> ❌")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


