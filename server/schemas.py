import datetime
from pydantic import BaseModel


class UserAdd(BaseModel):
    tg_id: str
    username: str | None
    firstname: str | None
    lastname: str | None
    phone: str | None = None


class User(UserAdd):
    id: int


class UserRel(User):
    subscription: list["Subscription"]


class Subscription(BaseModel):
    id: int
    active: bool
    start_date: datetime.datetime | None
    expire_date: datetime.datetime | None


class SubscriptionRel(Subscription):
    user: list["User"]


class ResponseResult(BaseModel):
    """Поля из ответа сервера Prodamus"""
    tg_id: str
    payment_status: str
    sing_is_good: bool
    customer_phone: str
    date_last_payment: datetime.datetime
    date_next_payment: datetime.datetime
