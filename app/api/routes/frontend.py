from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from loguru import logger

from app import frontend_repositories as repositories
from app import frontend_schemas as schemas
from app.core.config import settings
from app.services.gift_recommendations import (
    GiftGenerationError,
    UnsafeGiftCategoriesError,
    generate_gifts,
)
from app.services.telegram_auth import TelegramInitDataError, verify_telegram_init_data

router = APIRouter(prefix="/api", tags=["frontend-api"])


@dataclass(frozen=True)
class CurrentUser:
    telegram_id: int
    profile: dict


def _parse_telegram_id(value: str | None) -> int:
    if value is None or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Telegram-Id header is required",
        )
    try:
        telegram_id = int(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Telegram-Id header must be a positive integer",
        ) from exc
    if telegram_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Telegram-Id header must be a positive integer",
        )
    return telegram_id


async def current_user(
    x_telegram_id: Annotated[str | None, Header(alias="X-Telegram-Id")] = None,
    x_telegram_handle: Annotated[str | None, Header(alias="X-Telegram-Handle")] = None,
    x_first_name: Annotated[str | None, Header(alias="X-First-Name")] = None,
    x_last_name: Annotated[str | None, Header(alias="X-Last-Name")] = None,
    x_telegram_init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
) -> CurrentUser:
    telegram_id = _parse_telegram_id(x_telegram_id)
    telegram_handle = x_telegram_handle
    first_name = x_first_name
    last_name = x_last_name

    if x_telegram_init_data and settings.telegram_bot_token is not None:
        try:
            init_user = verify_telegram_init_data(x_telegram_init_data)
        except TelegramInitDataError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram initData verification failed",
            ) from exc
        if init_user.telegram_id != telegram_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram identity mismatch",
            )
        telegram_handle = init_user.telegram_handle or telegram_handle
        first_name = init_user.first_name or first_name
        last_name = init_user.last_name or last_name
    elif x_telegram_init_data:
        logger.warning("X-Telegram-Init-Data received but TELEGRAM_BOT_TOKEN is not configured")

    profile = await repositories.get_or_create_user(
        telegram_id=telegram_id,
        telegram_handle=telegram_handle,
        first_name=first_name,
        last_name=last_name,
    )
    return CurrentUser(telegram_id=telegram_id, profile=profile)


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]


@router.get("/auth/me", response_model=schemas.UserRead)
async def get_me(user: CurrentUserDep):
    return user.profile


@router.patch("/auth/profile", response_model=schemas.UserRead)
async def patch_profile(payload: schemas.CurrentUserPatch, user: CurrentUserDep):
    updated = await repositories.patch_user_profile(user.telegram_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated


@router.get("/settings", response_model=schemas.SettingsRead)
async def get_settings(user: CurrentUserDep):
    return await repositories.get_user_settings(user.telegram_id)


@router.patch("/settings", response_model=schemas.SettingsRead)
async def patch_settings(payload: schemas.SettingsPatch, user: CurrentUserDep):
    return await repositories.patch_user_settings(user.telegram_id, payload)


@router.post("/contacts", response_model=schemas.ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(payload: schemas.ContactCreate, user: CurrentUserDep):
    return await repositories.create_contact(user.telegram_id, payload)


@router.get("/contacts", response_model=list[schemas.ContactRead])
async def list_contacts(
    user: CurrentUserDep,
    include_archived: Annotated[bool, Query(alias="includeArchived")] = False,
):
    return await repositories.list_contacts(user.telegram_id, include_archived)


@router.get("/contacts/{contact_id}", response_model=schemas.ProfileRead)
async def get_contact(contact_id: UUID, user: CurrentUserDep):
    contact = await repositories.get_contact(user.telegram_id, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    notes = await repositories.list_notes(user.telegram_id, contact_id)
    widgets = await repositories.list_widgets(user.telegram_id, contact_id)
    reminders = await repositories.list_reminders(user.telegram_id, contact_id)
    return {
        **contact,
        "additional_notes": notes or [],
        "widgets": widgets or [],
        "reminders": reminders or [],
    }


@router.patch("/contacts/{contact_id}", response_model=schemas.ContactRead)
async def patch_contact(contact_id: UUID, payload: schemas.ContactPatch, user: CurrentUserDep):
    contact = await repositories.patch_contact(user.telegram_id, contact_id, payload)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: UUID, user: CurrentUserDep):
    success = await repositories.archive_contact(user.telegram_id, contact_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/contacts/{contact_id}/notes",
    response_model=schemas.NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(contact_id: UUID, payload: schemas.NoteCreate, user: CurrentUserDep):
    note = await repositories.create_note(user.telegram_id, contact_id, payload)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return note


@router.get("/contacts/{contact_id}/notes", response_model=list[schemas.NoteRead])
async def list_notes(contact_id: UUID, user: CurrentUserDep):
    notes = await repositories.list_notes(user.telegram_id, contact_id)
    if notes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return notes


@router.patch("/contacts/{contact_id}/notes/{note_id}", response_model=schemas.NoteRead)
async def patch_note(
    contact_id: UUID,
    note_id: UUID,
    payload: schemas.NotePatch,
    user: CurrentUserDep,
):
    note = await repositories.patch_note(user.telegram_id, contact_id, note_id, payload)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.delete("/contacts/{contact_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(contact_id: UUID, note_id: UUID, user: CurrentUserDep):
    success = await repositories.delete_note(user.telegram_id, contact_id, note_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/contacts/{contact_id}/widgets",
    response_model=schemas.WidgetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_widget(contact_id: UUID, payload: schemas.WidgetCreate, user: CurrentUserDep):
    widget = await repositories.create_widget(user.telegram_id, contact_id, payload)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return widget


@router.get("/contacts/{contact_id}/widgets", response_model=list[schemas.WidgetRead])
async def list_widgets(contact_id: UUID, user: CurrentUserDep):
    widgets = await repositories.list_widgets(user.telegram_id, contact_id)
    if widgets is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return widgets


@router.patch("/contacts/{contact_id}/widgets/{widget_id}", response_model=schemas.WidgetRead)
async def patch_widget(
    contact_id: UUID,
    widget_id: UUID,
    payload: schemas.WidgetPatch,
    user: CurrentUserDep,
):
    widget = await repositories.patch_widget(user.telegram_id, contact_id, widget_id, payload)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return widget


@router.delete("/contacts/{contact_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(contact_id: UUID, widget_id: UUID, user: CurrentUserDep):
    success = await repositories.delete_widget(user.telegram_id, contact_id, widget_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/contacts/{contact_id}/recommendations",
    response_model=schemas.GiftRecommendationSessionRead,
)
async def generate_gift_recommendations(
    contact_id: UUID,
    payload: schemas.GiftRecommendationRequest,
    user: CurrentUserDep,
):
    context = await repositories.get_contact_recommendation_context(user.telegram_id, contact_id)
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    notes = "\n".join(part for part in [context["notes"], payload.notes] if part)
    try:
        result = await generate_gifts(
            name=context["name"],
            birth_date=context["birth_date"].isoformat() if context["birth_date"] else None,
            categories=payload.categories,
            notes=notes or None,
        )
    except UnsafeGiftCategoriesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Categories look unsafe or empty",
        ) from exc
    except GiftGenerationError as exc:
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "credentials" in str(exc).lower()
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    saved = await repositories.save_gift_recommendation(
        telegram_id=user.telegram_id,
        contact_public_id=contact_id,
        categories=payload.categories,
        result=result,
        save_as_widgets=payload.save_as_widgets,
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return saved


@router.get(
    "/contacts/{contact_id}/recommendations",
    response_model=list[schemas.GiftRecommendationSessionRead],
)
async def list_gift_recommendations(contact_id: UUID, user: CurrentUserDep):
    recommendations = await repositories.list_gift_recommendations(user.telegram_id, contact_id)
    if recommendations is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return recommendations


@router.post("/reminders", response_model=schemas.ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(payload: schemas.ReminderCreate, user: CurrentUserDep):
    reminder = await repositories.create_reminder(user.telegram_id, payload)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return reminder


@router.get("/reminders", response_model=list[schemas.ReminderRead])
async def list_reminders(
    user: CurrentUserDep,
    contact_id: Annotated[UUID | None, Query(alias="contactId")] = None,
    upcoming: bool = False,
):
    reminders = await repositories.list_reminders(user.telegram_id, contact_id, upcoming)
    if reminders is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return reminders


@router.patch("/reminders/{reminder_id}", response_model=schemas.ReminderRead)
async def patch_reminder(reminder_id: UUID, payload: schemas.ReminderPatch, user: CurrentUserDep):
    reminder = await repositories.patch_reminder(user.telegram_id, reminder_id, payload)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(reminder_id: UUID, user: CurrentUserDep):
    success = await repositories.delete_reminder(user.telegram_id, reminder_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
