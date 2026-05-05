from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app import frontend_repositories as repositories
from app import frontend_schemas as schemas
from app.services.gift_recommendations import (
    GiftGenerationError,
    UnsafeGiftCategoriesError,
    generate_gifts,
)

router = APIRouter(prefix="/api", tags=["frontend-api"])


async def current_telegram_id(
    x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id")] = None,
) -> int:
    if x_telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Telegram-Id header is required",
        )
    return x_telegram_id


@router.get("/auth/me", response_model=schemas.UserRead)
async def get_me(
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
    telegram_handle: Annotated[str | None, Header(alias="X-Telegram-Handle")] = None,
    first_name: Annotated[str | None, Header(alias="X-First-Name")] = None,
    last_name: Annotated[str | None, Header(alias="X-Last-Name")] = None,
):
    return await repositories.get_or_create_user(
        telegram_id=telegram_id,
        telegram_handle=telegram_handle,
        first_name=first_name,
        last_name=last_name,
    )


@router.patch("/auth/profile", response_model=schemas.UserRead)
async def patch_profile(
    payload: schemas.CurrentUserPatch,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    user = await repositories.patch_user_profile(telegram_id, payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/contacts", response_model=schemas.ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: schemas.ContactCreate,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    await repositories.get_or_create_user(telegram_id)
    return await repositories.create_contact(telegram_id, payload)


@router.get("/contacts", response_model=list[schemas.ContactRead])
async def list_contacts(
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
    include_archived: Annotated[bool, Query(alias="includeArchived")] = False,
):
    await repositories.get_or_create_user(telegram_id)
    return await repositories.list_contacts(telegram_id, include_archived)


@router.get("/contacts/{contact_id}", response_model=schemas.ProfileRead)
async def get_contact(
    contact_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    await repositories.get_or_create_user(telegram_id)
    contact = await repositories.get_contact(telegram_id, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    notes = await repositories.list_notes(telegram_id, contact_id)
    widgets = await repositories.list_widgets(telegram_id, contact_id)
    reminders = await repositories.list_reminders(telegram_id, contact_id)
    return {
        **contact,
        "additional_notes": notes or [],
        "widgets": widgets,
        "reminders": reminders,
    }


@router.patch("/contacts/{contact_id}", response_model=schemas.ContactRead)
async def patch_contact(
    contact_id: UUID,
    payload: schemas.ContactPatch,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    contact = await repositories.patch_contact(telegram_id, contact_id, payload)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.delete("/contacts/{contact_id}", response_model=schemas.SuccessResponse)
async def delete_contact(
    contact_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    success = await repositories.archive_contact(telegram_id, contact_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return {"success": True}


@router.post(
    "/contacts/{contact_id}/notes",
    response_model=schemas.NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    contact_id: UUID,
    payload: schemas.NoteCreate,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    note = await repositories.create_note(telegram_id, contact_id, payload)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return note


@router.get("/contacts/{contact_id}/notes", response_model=list[schemas.NoteRead])
async def list_notes(
    contact_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    notes = await repositories.list_notes(telegram_id, contact_id)
    if notes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return notes


@router.patch("/contacts/{contact_id}/notes/{note_id}", response_model=schemas.NoteRead)
async def patch_note(
    contact_id: UUID,
    note_id: UUID,
    payload: schemas.NotePatch,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    note = await repositories.patch_note(telegram_id, contact_id, note_id, payload)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.delete("/contacts/{contact_id}/notes/{note_id}", response_model=schemas.SuccessResponse)
async def delete_note(
    contact_id: UUID,
    note_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    success = await repositories.delete_note(telegram_id, contact_id, note_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return {"success": True}


@router.post(
    "/contacts/{contact_id}/widgets",
    response_model=schemas.WidgetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_widget(
    contact_id: UUID,
    payload: schemas.WidgetCreate,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    widget = await repositories.create_widget(telegram_id, contact_id, payload)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return widget


@router.get("/contacts/{contact_id}/widgets", response_model=list[schemas.WidgetRead])
async def list_widgets(
    contact_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    return await repositories.list_widgets(telegram_id, contact_id)


@router.patch("/contacts/{contact_id}/widgets/{widget_id}", response_model=schemas.WidgetRead)
async def patch_widget(
    contact_id: UUID,
    widget_id: UUID,
    payload: schemas.WidgetPatch,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    widget = await repositories.patch_widget(telegram_id, contact_id, widget_id, payload)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return widget


@router.delete("/contacts/{contact_id}/widgets/{widget_id}", response_model=schemas.SuccessResponse)
async def delete_widget(
    contact_id: UUID,
    widget_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    success = await repositories.delete_widget(telegram_id, contact_id, widget_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return {"success": True}


@router.post(
    "/contacts/{contact_id}/recommendations",
    response_model=schemas.GiftRecommendationSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_gift_recommendations(
    contact_id: UUID,
    payload: schemas.GiftRecommendationRequest,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    await repositories.get_or_create_user(telegram_id)
    context = await repositories.get_contact_recommendation_context(telegram_id, contact_id)
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
        telegram_id=telegram_id,
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
async def list_gift_recommendations(
    contact_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    return await repositories.list_gift_recommendations(telegram_id, contact_id)


@router.post("/reminders", response_model=schemas.ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: schemas.ReminderCreate,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    reminder = await repositories.create_reminder(telegram_id, payload)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return reminder


@router.get("/reminders", response_model=list[schemas.ReminderRead])
async def list_reminders(
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
    contact_id: Annotated[UUID | None, Query(alias="contactId")] = None,
    upcoming: bool = False,
):
    return await repositories.list_reminders(telegram_id, contact_id, upcoming)


@router.patch("/reminders/{reminder_id}", response_model=schemas.ReminderRead)
async def patch_reminder(
    reminder_id: UUID,
    payload: schemas.ReminderPatch,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    reminder = await repositories.patch_reminder(telegram_id, reminder_id, payload)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


@router.delete("/reminders/{reminder_id}", response_model=schemas.SuccessResponse)
async def delete_reminder(
    reminder_id: UUID,
    telegram_id: Annotated[int, Header(alias="X-Telegram-Id")],
):
    success = await repositories.delete_reminder(telegram_id, reminder_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return {"success": True}
