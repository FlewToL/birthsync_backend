from __future__ import annotations

import re
from datetime import date as dt_date, datetime, time as dt_time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+()\-\s.]{1,20}$")
TELEGRAM_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")

ImageValue = str | None
Accent = Literal["gray", "red", "blue", "green", "yellow", "purple"]
ReminderRepeat = Literal["daily", "weekly", "monthly", "yearly"]
EarlyReminderRepeat = Literal["once", "daily"]
Theme = Literal["system", "light", "dark"]


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def validate_email(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if not EMAIL_RE.match(value):
        raise ValueError("Invalid email format")
    return value


def validate_phone(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if not PHONE_RE.match(value):
        raise ValueError("Invalid phone format")
    return value


def validate_telegram_handle(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    value = value.removeprefix("@")
    if not TELEGRAM_HANDLE_RE.match(value):
        raise ValueError("Invalid Telegram handle")
    return value


def validate_image_value(value: ImageValue) -> ImageValue:
    if value is None or value == "":
        return value
    if len(value) > 1_048_576:
        raise ValueError("Image value is too large")
    if value.startswith(("http://", "https://", "data:image/")):
        return value
    raise ValueError("Image must be an HTTP(S) URL or data:image base64 value")


def validate_http_url(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    raise ValueError("URL must start with http:// or https://")


class FrontendModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class CurrentUserPatch(FrontendModel):
    telegram_handle: str | None = Field(default=None, max_length=32)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    birth_date: dt_date | None = None
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    profile_image: ImageValue = None
    common_notes: str | None = Field(default=None, max_length=5000)
    preferred_language: str | None = Field(default=None, max_length=8)

    _validate_email = field_validator("email")(validate_email)
    _validate_phone = field_validator("phone")(validate_phone)
    _validate_telegram_handle = field_validator("telegram_handle")(validate_telegram_handle)
    _validate_profile_image = field_validator("profile_image")(validate_image_value)


class UserRead(FrontendModel):
    id: str
    telegram_id: int
    telegram_handle: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    birth_date: dt_date | None = None
    phone: str | None = None
    email: str | None = None
    profile_image: str | None = None
    common_notes: str | None = None
    preferred_language: str = "ru"
    created_at: datetime
    updated_at: datetime


class WidgetLink(FrontendModel):
    text: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2048)

    _validate_url = field_validator("url")(validate_http_url)


class NoteRead(FrontendModel):
    id: UUID
    contact_id: UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class WidgetRead(FrontendModel):
    id: UUID
    contact_id: UUID
    title: str
    description: str | None = None
    image_url: str | None = None
    price: str | None = None
    links: list[WidgetLink] = Field(default_factory=list)
    accent: Accent = "gray"
    created_at: datetime
    updated_at: datetime


class ReminderRead(FrontendModel):
    id: UUID
    contact_id: UUID
    title: str
    description: str | None = None
    date: dt_date
    time: dt_time | None = None
    completed: bool
    repeat: ReminderRepeat | None = None
    early_reminder_minutes: int | None = None
    early_reminder_repeat: EarlyReminderRepeat | None = None
    created_at: datetime
    updated_at: datetime


class ContactRead(FrontendModel):
    id: UUID
    name: str
    relation: str | None = None
    telegram_handle: str | None = None
    birth_date: dt_date | None = None
    phone: str | None = None
    email: str | None = None
    profile_image: str | None = None
    common_notes: str | None = None
    additional_notes: list[NoteRead] = Field(default_factory=list)
    widgets: list[WidgetRead] = Field(default_factory=list)
    reminders: list[ReminderRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False


class ContactCreate(FrontendModel):
    name: str = Field(min_length=1, max_length=255)
    relation: str | None = Field(default=None, max_length=100)
    telegram_handle: str | None = Field(default=None, max_length=32)
    birth_date: dt_date | None = None
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    profile_image: ImageValue = None
    common_notes: str | None = Field(default=None, max_length=5000)

    _validate_email = field_validator("email")(validate_email)
    _validate_phone = field_validator("phone")(validate_phone)
    _validate_telegram_handle = field_validator("telegram_handle")(validate_telegram_handle)
    _validate_profile_image = field_validator("profile_image")(validate_image_value)


class ContactPatch(FrontendModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    relation: str | None = Field(default=None, max_length=100)
    telegram_handle: str | None = Field(default=None, max_length=32)
    birth_date: dt_date | None = None
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    profile_image: ImageValue = None
    common_notes: str | None = Field(default=None, max_length=5000)
    is_archived: bool | None = None

    _validate_email = field_validator("email")(validate_email)
    _validate_phone = field_validator("phone")(validate_phone)
    _validate_telegram_handle = field_validator("telegram_handle")(validate_telegram_handle)
    _validate_profile_image = field_validator("profile_image")(validate_image_value)


class NoteCreate(FrontendModel):
    title: str = Field(min_length=1, max_length=255)
    content: str | None = Field(default="", max_length=5000)


class NotePatch(FrontendModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, max_length=5000)


class WidgetCreate(FrontendModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    image_url: ImageValue = None
    price: str | None = Field(default=None, max_length=50)
    links: list[WidgetLink] = Field(default_factory=list, max_length=10)
    accent: Accent = "gray"

    _validate_image_url = field_validator("image_url")(validate_image_value)


class WidgetPatch(FrontendModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    image_url: ImageValue = None
    price: str | None = Field(default=None, max_length=50)
    links: list[WidgetLink] | None = Field(default=None, max_length=10)
    accent: Accent | None = None

    _validate_image_url = field_validator("image_url")(validate_image_value)


class ReminderCreate(FrontendModel):
    contact_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    date: dt_date
    time: dt_time | None = None
    completed: bool = False
    repeat: ReminderRepeat | None = None
    early_reminder_minutes: int | None = Field(default=None, ge=0, le=525600)
    early_reminder_repeat: EarlyReminderRepeat | None = None


class ReminderPatch(FrontendModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    date: dt_date | None = None
    time: dt_time | None = None
    completed: bool | None = None
    repeat: ReminderRepeat | None = None
    early_reminder_minutes: int | None = Field(default=None, ge=0, le=525600)
    early_reminder_repeat: EarlyReminderRepeat | None = None


class ProfileRead(ContactRead):
    pass


class GiftRecommendationRequest(FrontendModel):
    categories: list[str] = Field(min_length=1, max_length=12)
    notes: str | None = Field(default=None, max_length=5000)
    save_as_widgets: bool = False


class GiftRecommendationItemRead(FrontendModel):
    id: int
    title: str
    description: str | None = None
    created_at: datetime


class GiftRecommendationSessionRead(FrontendModel):
    id: int
    contact_id: UUID
    provider: str
    model_name: str | None = None
    raw_response: str
    items: list[GiftRecommendationItemRead]
    created_at: datetime


class SettingsRead(FrontendModel):
    theme: Theme = "system"
    swipe_enabled: bool = True
    notifications_enabled: bool = True
    birthday_reminder_days: int = Field(default=1, ge=0, le=365)
    gift_recommendations_enabled: bool = True
    created_at: datetime
    updated_at: datetime


class SettingsPatch(FrontendModel):
    theme: Theme | None = None
    swipe_enabled: bool | None = None
    notifications_enabled: bool | None = None
    birthday_reminder_days: int | None = Field(default=None, ge=0, le=365)
    gift_recommendations_enabled: bool | None = None
