import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from database import async_session_factory
import tables
import schemas


class AsyncOrm:

    @staticmethod
    async def get_user_with_subscription_by_tg_id(tg_id: str) -> schemas.UserRel:
        """Получение подписки и связанного пользователя по tg id"""
        async with async_session_factory() as session:
            query = select(tables.User)\
                .where(tables.User.tg_id == tg_id)\
                .options(joinedload(tables.User.subscription))

            result = await session.execute(query)
            row = result.scalars().first()
            user = schemas.UserRel.model_validate(row, from_attributes=True)

            return user

    @staticmethod
    async def update_subscribe(subscription_id: int, start_date: datetime.datetime, expire_date: datetime.datetime) -> None:
        """Оформление подписки"""
        async with async_session_factory() as session:
            query = update(tables.Subscription) \
                .where(tables.Subscription.id == subscription_id) \
                .values(active=True, start_date=start_date, expire_date=expire_date)

            await session.execute(query)
            await session.flush()
            await session.commit()

    @staticmethod
    async def update_user_phone(user_id: int, phone_number: str) -> None:
        """Запись телефона пользователю"""
        async with async_session_factory() as session:
            query = update(tables.User)\
                .where(tables.User.id == user_id)\
                .values(phone=phone_number)

            await session.execute(query)
            await session.flush()
            await session.commit()
