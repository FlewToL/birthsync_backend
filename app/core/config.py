from datetime import time

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


OWNER_ID = 435918797
ADMINS_LIST = (435918797,)
BANNED_USERS = ()


class EnvBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class AppSettings(EnvBaseSettings):
    app_name: str = "BirthSync API"
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    log_json: bool = False
    log_to_file: bool = True
    log_file_path: str = "logs/app.log"
    log_file_rotation: str = "00:00"
    log_file_retention: str = "365 days"
    db_apply_schema_on_startup: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    cors_origin_regex: str | None = None


class DBSettings(EnvBaseSettings):
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "birthsync"
    db_pass: SecretStr = SecretStr("birthsync")
    db_name: str = "birthsync"

    @property
    def database_url_asyncpg(self) -> str:
        password = self.db_pass.get_secret_value()
        return f"postgresql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"


class CacheSettings(EnvBaseSettings):
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_pass: str | None = None
    redis_db: int = 3


class GigaChatSettings(EnvBaseSettings):
    credentials: SecretStr | None = None
    gigachat_model: str = "GigaChat-Pro"
    gigachat_verify_ssl_certs: bool = False


class TelegramSettings(EnvBaseSettings):
    telegram_bot_token: SecretStr | None = None
    telegram_init_data_max_age_seconds: int = 86400
    telegram_bot_polling_enabled: bool = False
    telegram_reminders_enabled: bool = True
    telegram_reminder_poll_interval_seconds: int = 60
    telegram_reminder_late_grace_minutes: int = 1440
    telegram_reminder_timezone: str = "Europe/Moscow"
    telegram_reminder_default_time: time = time(hour=9, minute=0)


class Settings(AppSettings, DBSettings, CacheSettings, GigaChatSettings, TelegramSettings):
    debug: bool = False


settings = Settings()
