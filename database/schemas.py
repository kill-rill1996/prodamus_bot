import datetime
from pydantic import BaseModel


class UserAdd(BaseModel):
    tg_id: str
    username: str | None
    firstname: str | None
    lastname: str | None


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

