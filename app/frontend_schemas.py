from __future__ import annotations

from datetime import date as dt_date, datetime, time as dt_time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class FrontendModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class SuccessResponse(FrontendModel):
    success: bool


class CurrentUserPatch(FrontendModel):
    telegram_handle: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    birth_date: dt_date | None = None
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    profile_image: str | None = None
    common_notes: str | None = None
    preferred_language: str | None = Field(default=None, max_length=8)


class UserRead(FrontendModel):
    id: str
    telegram_id: int
    telegram_handle: str | None = None
    first_name: str
    last_name: str | None = None
    birth_date: dt_date | None = None
    phone: str | None = None
    email: str | None = Field(default=None, max_length=255)
    profile_image: str | None = None
    common_notes: str | None = None
    preferred_language: str = "ru"
    created_at: datetime
    updated_at: datetime


class ContactCreate(FrontendModel):
    name: str = Field(min_length=1, max_length=255)
    relation: str | None = Field(default=None, max_length=100)
    telegram_handle: str | None = Field(default=None, max_length=255)
    birth_date: dt_date | None = None
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    profile_image: str | None = None
    common_notes: str | None = None


class ContactPatch(FrontendModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    relation: str | None = Field(default=None, max_length=100)
    telegram_handle: str | None = Field(default=None, max_length=255)
    birth_date: dt_date | None = None
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = None
    profile_image: str | None = None
    common_notes: str | None = None
    is_archived: bool | None = None


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
    additional_notes: list[str] = []
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False


class NoteCreate(FrontendModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class NotePatch(FrontendModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)


class NoteRead(FrontendModel):
    id: UUID
    contact_id: UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class WidgetLink(FrontendModel):
    text: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)


class WidgetCreate(FrontendModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = None
    price: str | None = Field(default=None, max_length=100)
    links: list[WidgetLink] = []
    accent: Literal["gray", "blue", "photo"] = "gray"


class WidgetPatch(FrontendModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = None
    price: str | None = Field(default=None, max_length=100)
    links: list[WidgetLink] | None = None
    accent: Literal["gray", "blue", "photo"] | None = None


class WidgetRead(FrontendModel):
    id: UUID
    contact_id: UUID
    title: str
    description: str | None = None
    image_url: str | None = None
    price: str | None = None
    links: list[WidgetLink] = []
    accent: Literal["gray", "blue", "photo"] = "gray"
    created_at: datetime
    updated_at: datetime


class ReminderCreate(FrontendModel):
    contact_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    date: dt_date
    time: dt_time | None = None
    completed: bool = False


class ReminderPatch(FrontendModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    date: dt_date | None = None
    time: dt_time | None = None
    completed: bool | None = None


class ReminderRead(FrontendModel):
    id: UUID
    contact_id: UUID
    title: str
    description: str | None = None
    date: dt_date
    time: dt_time | None = None
    completed: bool
    created_at: datetime
    updated_at: datetime


class ProfileRead(ContactRead):
    additional_notes: list[NoteRead] = []
    widgets: list[WidgetRead] = []
    reminders: list[ReminderRead] = []


class GiftRecommendationRequest(FrontendModel):
    categories: list[str] = Field(min_length=1, max_length=12)
    notes: str | None = None
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
