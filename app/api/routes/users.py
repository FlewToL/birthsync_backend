import asyncpg
from fastapi import APIRouter, HTTPException, status

from app import repositories, schemas

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: schemas.UserCreate):
    return await repositories.create_user(payload)


@router.get("/telegram/{telegram_id}", response_model=schemas.UserRead)
async def get_user_by_telegram_id(telegram_id: int):
    user = await repositories.get_user_by_telegram_id(telegram_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}", response_model=schemas.UserRead)
async def get_user(user_id: int):
    user = await repositories.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}/card", response_model=schemas.UserCardRead)
async def upsert_user_card(user_id: int, payload: schemas.UserCardUpsert):
    try:
        return await repositories.upsert_user_card(user_id, payload)
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc


@router.get("/{user_id}/card", response_model=schemas.UserCardRead)
async def get_user_card(user_id: int):
    card = await repositories.get_user_card(user_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User card not found")
    return card


@router.get("/{user_id}/contacts", response_model=list[schemas.ContactRead])
async def list_contacts(user_id: int):
    return await repositories.list_contacts(user_id)


@router.get("/{user_id}/categories", response_model=list[schemas.CategoryRead])
async def list_categories(user_id: int):
    return await repositories.list_categories(user_id)


@router.get("/{user_id}/wishlists", response_model=list[schemas.WishlistRead])
async def list_wishlists(user_id: int):
    return await repositories.list_wishlists(user_id)
