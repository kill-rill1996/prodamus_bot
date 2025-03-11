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
    prev_mess = await callback.message.edit_text(msg, reply_markup=kb.cancel_keyboard().as_markup())
    await state.update_data(prev_mess=prev_mess)


@router.message(SendMessagesFSM.text)
async def send_messages_to_users(message: types.Message, state: FSMContext, bot: aiogram.Bot) -> None:
    """Рассылка сообщения для пользователей"""
    # удаление предыдущего сообщения
    data = await state.get_data()
    prev_mess = data["prev_mess"]
    try:
        await prev_mess.delete()
    except Exception:
        pass

    # сообщение об осуществлении отправки
    wait_text = "⏳ Выполняется рассылка..."
    wait_msg = await message.answer(wait_text)

    await state.clear()

    msg = message.text
    operations = await AsyncOrm.get_unsub_operations()
    unique_operations = {}

    for operation in operations:
        # пропуск дубликатов
        if operation.tg_id in unique_operations:
            continue
        # отправка сообщений
        try:
            unique_operations[operation.tg_id] = True
            await bot.send_message(operation.tg_id, msg)

        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю при оповещении отписавшихся {operation.tg_id}: {e}")

    await wait_msg.edit_text("✅ Пользователи оповещены")


@router.callback_query(lambda callback: callback.data == "button_cancel", StateFilter("*"))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel FSM and delete last message"""
    await state.clear()
    await callback.message.answer("<b>Действие отменено</b> ❌")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


