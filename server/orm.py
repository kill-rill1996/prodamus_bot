import datetime
from typing import List

import pytz
from sqlalchemy import select, delete, update, text, and_
from sqlalchemy.orm import joinedload, selectinload

import settings
from database import async_engine, async_session_factory
from tables import Base
import tables
import schemas


class AsyncOrm:

    # @staticmethod
    # async def create_tables():
    #     """Создание таблиц"""
    #     async with async_engine.begin() as conn:
    #         await conn.run_sync(Base.metadata.drop_all)
    #         await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def get_user_by_tg_id(tg_id: str) -> schemas.User:
        """Получение пользователя по tg_id"""
        async with async_session_factory() as session:
            query = select(tables.User)\
                .where(tables.User.tg_id == tg_id)

            result = await session.execute(query)
            row = result.scalars().first()
            user = schemas.User.model_validate(row, from_attributes=True)
            return user

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
    async def update_subscribe(subscription_id: int) -> None:
        """Оформление подписки"""
        async with async_session_factory() as session:
            start_date = (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow"))).date()
            expire_date = (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) + datetime.timedelta(days=30)).date()

            query = update(tables.Subscription) \
                .where(tables.Subscription.id == subscription_id) \
                .values(active=True, start_date=start_date, expire_date=expire_date)

            await session.execute(query)
            await session.flush()
            await session.commit()
    #
    # @staticmethod
    # async def update_sub_by_user_id(user_id: int) -> None:
    #     """Обновление подписки по id пользователя"""
    #     async with async_session_factory() as session:
    #         start_date = (datetime.datetime.now(tz=pytz.timezone("Europe/Moscow"))).date()
    #         expire_date = (
    #                     datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")) + datetime.timedelta(days=30)).date()
    #
    #         query = update(tables.Subscription) \
    #             .where(tables.Subscription.user_id == user_id) \
    #             .values(active=True, start_date=start_date, expire_date=expire_date)
    #
    #         await session.execute(query)
    #         await session.flush()
    #         await session.commit()
    #
    # @staticmethod
    # async def create_payment(user_id: int):
    #     async with async_session_factory() as session:
    #         payment = tables.Payments(
    #             user_id=user_id,
    #             date=datetime.datetime.now(tz=pytz.timezone("Europe/Moscow")).date())
    #
    #         session.add(payment)
    #
    #         await session.flush()
    #         await session.commit()