import datetime
from typing import List

from sqlalchemy import select, delete, update, text, and_
from sqlalchemy.orm import joinedload, selectinload

import settings
from database.database import async_engine, async_session_factory
from database.tables import Base
from database import schemas
from database import tables


class AsyncOrm:

    @staticmethod
    async def create_tables():
        """Создание таблиц"""
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def create_user(new_user: schemas.UserAdd) -> int:
        """Создание пользователя и подписки в базе данных"""
        async with async_session_factory() as session:
            user = tables.User(**new_user.dict())
            session.add(user)

            await session.flush()
            user_id = user.id
            await session.commit()
            return user_id

    @staticmethod
    async def create_subscription(user_id: int) -> None:
        """Создание подписки пользователю"""
        async with async_session_factory() as session:
            subscription = tables.Subscription(
                user_id=user_id
            )
            session.add(subscription)
            await session.flush()
            await session.commit()

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


