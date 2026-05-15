from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from loguru import logger

from app.core.config import settings


class TelegramInitDataError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramInitUser:
    telegram_id: int
    telegram_handle: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def verify_telegram_init_data(init_data: str) -> TelegramInitUser:
    if settings.telegram_bot_token is None or not settings.telegram_bot_token.get_secret_value().strip():
        raise TelegramInitDataError("Telegram bot token is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("Telegram initData hash is missing")

    auth_date = pairs.get("auth_date")
    if auth_date is None:
        raise TelegramInitDataError("Telegram initData auth_date is missing")
    try:
        auth_timestamp = int(auth_date)
    except ValueError as exc:
        raise TelegramInitDataError("Telegram initData auth_date is invalid") from exc

    max_age = settings.telegram_init_data_max_age_seconds
    if max_age > 0 and time.time() - auth_timestamp > max_age:
        raise TelegramInitDataError("Telegram initData is expired")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    bot_token = settings.telegram_bot_token.get_secret_value()
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        logger.warning("Telegram initData signature verification failed")
        raise TelegramInitDataError("Telegram initData signature is invalid")

    raw_user = pairs.get("user")
    if raw_user is None:
        raise TelegramInitDataError("Telegram initData user payload is missing")
    try:
        user = json.loads(raw_user)
        telegram_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TelegramInitDataError("Telegram initData user payload is invalid") from exc

    return TelegramInitUser(
        telegram_id=telegram_id,
        telegram_handle=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
    )
