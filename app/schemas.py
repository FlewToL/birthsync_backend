from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    telegram_id: int | None = None
    username: str | None = Field(default=None, max_length=255)


class UserRead(BaseModel):
    id: int
    telegram_id: int | None
    username: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCardUpsert(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None
    about: str | None = None


class UserCardRead(UserCardUpsert):
    user_id: int
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    owner_user_id: int
    contact_user_id: int | None = None
    display_name: str = Field(min_length=1, max_length=255)
    relation: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    status: Literal["pending", "confirmed", "declined"] = "pending"


class ContactRead(ContactCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class CategoryCreate(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=100)


class CategoryRead(CategoryCreate):
    id: int
    created_at: datetime


class WishlistCreate(BaseModel):
    owner_user_id: int
    contact_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WishlistRead(WishlistCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class WishlistItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    url: str | None = Field(default=None, max_length=2048)


class WishlistItemRead(WishlistItemCreate):
    id: int
    wishlist_id: int
    status: Literal["active", "reserved", "bought", "archived"]
    created_at: datetime
    updated_at: datetime
