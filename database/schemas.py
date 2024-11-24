import datetime

from pydantic import BaseModel


class UserAdd(BaseModel):
    tg_id: str
    username: str | None
    firstname: str | None
    lastname: str | None


class User(UserAdd):
    id: int

