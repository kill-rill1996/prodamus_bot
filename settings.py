from pydantic_settings import BaseSettings, SettingsConfigDict


class Database(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    bot_token: str
    admins: list
    channel_id: str
    price: int = 50
    sub_number: int
    pay_link: str
    pay_token: str
    invite_link: str
    trial_period: int = 3
    trial_discount: int = 889

    db: Database = Database()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
