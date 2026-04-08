import aiogram
from aiogram import Router, types, F, Bot
from aiogram.types import ContentType as CT, FSInputFile
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils import keyboard
from aiogram.utils.media_group import MediaGroupBuilder

from middlewares.media import MediaMiddleware
from routers.keyboards import cancel_keyboard, invite_to_channel_keyboard, get_access_keyboard
from settings import settings
from routers import keyboards as kb
from routers.fsm_states import SendMessagesFSM, AddUser
from database.orm import AsyncOrm
from routers.utils import generate_excel_file

router = Router()


@router.callback_query(lambda c: c.data == "menu_administration")
async def admin_menu(callback: types.CallbackQuery) -> None:
    """Меню администратора"""
    msg = "Панель администратора"
    await callback.message.edit_text(msg, reply_markup=kb.admin_keyboard().as_markup())


@router.callback_query(lambda c: c.data == "notify_users")
async def choose_users(callback: types.CallbackQuery) -> None:
    """Выбор списка пользователей для отправки сообщения"""
    msg = "\"<b>Всем пользователям</b>\" - рассылка сообщения всем пользователям в боте\n\n" \
          "\"<b>Польз. без подписки</b>\" - рассылка сообщения пользователям с неактивной подпиской " \
          "(отмененной или еще не оформленной подпиской)\n\n" \
          "\"<b>Отменившим подписку</b>\" - рассылка сообщения пользователям, которые отменили подписку"

    await callback.message.edit_text(msg, reply_markup=kb.admin_users_group().as_markup())


@router.callback_query(lambda c: c.data.split("_")[0] == "users-group")
async def notify_users(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Подготовка сообщения для пользователей"""
    user_group = callback.data.split("_")[1]

    await state.set_state(SendMessagesFSM.text)
    await state.update_data(user_group=user_group)

    msg = "Отправьте в чат сообщение, которое вы бы хотели разослать "
    if user_group == "all":
        msg += "всем пользователям"
    elif user_group == "inactive":
        msg += "пользователям, еще не оформившим или отменившим подписку"
    else:
        msg += "пользователям, которые отменили подписку"

    prev_mess = await callback.message.edit_text(msg, reply_markup=kb.skip_message_or_cancel_keyboard().as_markup())
    await state.update_data(prev_mess=prev_mess)


@router.message(SendMessagesFSM.text)
@router.callback_query(SendMessagesFSM.text, lambda c: c.data == "button_skip_message")
async def get_message_for_users(message: types.Message | types.CallbackQuery, state: FSMContext) -> None:
    """Получение сообщения для пользователей и переход в SendMessagesFSM.media"""
    # редактирование предыдущего сообщения
    data = await state.get_data()
    prev_mess = data["prev_mess"]
    try:
        await prev_mess.edit_text(prev_mess.text)
    except Exception:
        pass

    # если ввели текст
    if type(message) == types.Message:
        if message.text:
            # сохраняем сообщение для пользователей
            await state.update_data(text=message.html_text)

        # при отправке не текста
        else:
            msg = "Сообщение должно быть <b>текстом</b>\n" \
                  "Попробуйте отправить еще раз"
            prev_mess = await message.answer(msg, reply_markup=kb.skip_message_or_cancel_keyboard().as_markup())
            await state.update_data(prev_mess=prev_mess)
            return

    # если нажали "Пропустить"
    else:
        await state.update_data(text=None)

    # переходим в следующий state
    await state.set_state(SendMessagesFSM.media)

    # сообщение с предложением отправить медиа
    msg = f"Отправьте <b>все фото и видео</b>, которые хотите приложить, <b>одним сообщением</b>\n\n" \
          f"Если хотите отправить <b>только текст</b> нажмите \"Пропустить\""

    if type(message) == types.Message:
        prev_mess = await message.answer(msg, reply_markup=kb.skip_media_or_cancel_keyboard().as_markup())
    else:
        prev_mess = await message.message.answer(msg, reply_markup=kb.skip_media_or_cancel_keyboard().as_markup())

    await state.update_data(prev_mess=prev_mess)


media_router = Router()
media_router.message.middleware.register(MediaMiddleware())


@media_router.message(SendMessagesFSM.media, F.content_type.in_([CT.PHOTO, CT.VIDEO, CT.DOCUMENT, CT.AUDIO, CT.VOICE]))
@media_router.callback_query(SendMessagesFSM.media, lambda c: c.data == "button_skip_media")
async def get_media_for_users_and_send_messages(message: types.Message | types.CallbackQuery,
                                                state: FSMContext,
                                                bot: aiogram.Bot,
                                                album: list[types.Message] = None) -> None:
    """Получение медиа для пользователей"""
    # получаем date из FSM state
    data = await state.get_data()
    await state.clear()

    # редактирование предыдущего сообщения
    prev_mess = data["prev_mess"]
    try:
        await prev_mess.edit_text(prev_mess.text)
    except Exception:
        pass

    # сообщение об осуществлении отправки
    wait_text = "⏳ Выполняется рассылка..."
    if type(message) == types.Message:
        wait_msg = await message.answer(wait_text)
    else:
        wait_msg = await message.message.answer(wait_text)

    msg = data["text"]

    # получаем list tg_id пользователей для рассылки
    user_group = data["user_group"]
    users_ids = await get_user_group_ids(user_group)

    success_message_counter = 0
    for tg_id in users_ids:

        # Не отправляем пользователям в списке исключения
        if not tg_id in settings.exclude_users_for_notify:

            # если не было передано медиа
            if type(message) == types.CallbackQuery:

                # только текст
                if msg:
                    await bot.send_message(tg_id, msg)
                    success_message_counter += 1

                # нет текста и медиа
                else:
                    await wait_msg.edit_text("Невозможно отправить пустое сообщение")
                    return

            else:
                # если в медиа передали некорректные файлы
                if not album:
                    await wait_msg.edit_text("Переданы некорректные типы файлов")
                    return

                # подготовка альбома
                media_group = MediaGroupBuilder(caption=msg)

                for obj in album:
                    if obj.photo:
                        file_id = obj.photo[-1].file_id
                        media_group.add_photo(type="photo", media=file_id)
                    elif obj.video:
                        obj_dict = obj.dict()
                        file_id = obj_dict[obj.content_type]['file_id']
                        media_group.add_video(type="video", media=file_id)
                    else:
                        await message.answer("Переданы некорректные типы файлов")
                        return

                try:
                    await bot.send_media_group(tg_id, media_group.build())
                    # TODO убрать если не нужна клавиатура к альбому отдельным сообщением
                    await bot.send_message(
                        tg_id,
                        "<b>Приложение Sheva Nutrition</b>\n\n"
                        "Подписываешься на канал, там будет на него ссылка 👇",
                        reply_markup=get_access_keyboard().as_markup())
                    success_message_counter += 1

                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю при оповещении {user_group} {tg_id}: {e}")

    await wait_msg.edit_text(f"✅ Оповещено пользователей: <b>{success_message_counter}</b>")


@router.callback_query(lambda callback: callback.data == "button_cancel", StateFilter("*"))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel FSM and delete last message"""
    await state.clear()
    await callback.message.answer("<b>Действие отменено</b> ❌")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


async def get_user_group_ids(user_group: str) -> list[str]:
    """Возвращает список tg_id пользователей"""
    if user_group == "all":
        users_ids = await AsyncOrm.get_all_tg_ids()
    elif user_group == "inactive":
        users_ids = await AsyncOrm.get_inactive_users_tg_ids()
    else:
        users_ids = await AsyncOrm.get_unsub_tg_ids()

    return users_ids


@router.message(Command("secret_command"))
async def send_messages_to_users(message: types.Message, bot: Bot) -> None:
    """Рассылка сообщения по определенным id"""

    if str(message.from_user.id) not in settings.admins:
        await message.answer("Функция доступна только администраторам")
        return

    users_ids = ["938764138", "1041847886", "933093469", "694321884", "625805988", "529889046", "1721915702",
                 "616455725", "345893866", "116115392", "1043596417"]

    for user_id in users_ids:
        link = await bot.create_chat_invite_link(settings.channel_id, member_limit=1)
        msg = f"✅ Ваша подписка успешно продлена\n\n" \
              f"Чтобы вступить в канал перейдите по ссылке ниже 👇\n\n{link.invite_link}"
        try:
            await bot.send_message(user_id, msg)

        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    await message.answer(f"✅ {len(users_ids)} пользователей успешно оповещены")


# TODO для приглашения пользователя в канал в ручную в случае неисправностей
@router.message(Command("add_user"))
async def add_user_in_channel(message: types.Message, state: FSMContext) -> None:
    """Приглашение пользователя в канал в ручную"""
    # Проверка на админа
    admin_tg_id = str(message.from_user.id)
    if admin_tg_id not in ["420551454", "714371204"]:
        await message.answer("Функция доступна только администраторам")
        return

    await state.set_state(AddUser.tg_id)
    keyboard = cancel_keyboard()
    await message.answer("Пришлите tg id пользователя для приглашения в канал",
                         reply_markup=keyboard.as_markup())


@router.message(StateFilter(AddUser.tg_id))
async def send_invite_to_user(message: types.Message, state: FSMContext, bot: Bot) -> None:
    # Получаем tg id пользователя для отправки приглашения
    try:
        user_tg_id = str(message.text)
    except Exception as e:
        await message.answer(f"Ошибка при обработке tg id, проверьте правильность написания: {e}")
        return

    # Очищаем стейт
    await state.clear()

    try:
        link = await bot.create_chat_invite_link(settings.channel_id, member_limit=1)
        text = "Статус подписки на закрытый канал с ежедневным питанием от Шевы:\n\n" \
               f"✅ <b>Активна</b>\n" \
               "<i>*Вы всегда можете отменить подписку через меню бота</i>\n\n" \
               "Ваша ссылка на вступление в закрытый канал\n\n" \
               "↓↓↓"
        keyboard = invite_to_channel_keyboard(link.invite_link)

        # Отправляем сообщение пользователю
        await bot.send_message(
            user_tg_id,
            text,
            reply_markup=keyboard.as_markup()
        )

        # Оповещаем админа
        await message.answer("Приглашение в группу успешно отправлено пользователю ")

    except Exception as e:
        await message.answer(f"Не удалось отправить сообщение пользователю: {e}")


@router.callback_query(lambda callback: callback.data == "button_cancel", StateFilter(AddUser.tg_id))
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено")


@router.callback_query(lambda callback: callback.data == "get_excel_users")
async def get_excel_users_data(callback: types.CallbackQuery):
    """Получение списка всех пользователей"""
    wait_msg = await callback.message.edit_text("⏳ Подождите, как только таблица сформируется, "
                                                "файл будет отправлен в чат")

    users = await AsyncOrm.get_all_users_with_active_subscription()

    # Generate excel file
    generate_excel_file(users)

    try:
        document = FSInputFile('users/users.xlsx')
        await callback.message.answer_document(document)
        await wait_msg.delete()

    except Exception as e:
        await callback.message.answer(f"Ошибка при формировании excel файла: {e}")




