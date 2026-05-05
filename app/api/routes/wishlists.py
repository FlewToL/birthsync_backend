import asyncpg
from fastapi import APIRouter, HTTPException, status

from app import repositories, schemas

router = APIRouter(prefix="/wishlists", tags=["wishlists"])


@router.post("", response_model=schemas.WishlistRead, status_code=status.HTTP_201_CREATED)
async def create_wishlist(payload: schemas.WishlistCreate):
    try:
        return await repositories.create_wishlist(payload)
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner user or contact does not exist",
        ) from exc


@router.get("/{wishlist_id}/items", response_model=list[schemas.WishlistItemRead])
async def list_wishlist_items(wishlist_id: int):
    return await repositories.list_wishlist_items(wishlist_id)


@router.post(
    "/{wishlist_id}/items",
    response_model=schemas.WishlistItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_wishlist_item(
    wishlist_id: int,
    payload: schemas.WishlistItemCreate,
):
    try:
        return await repositories.create_wishlist_item(wishlist_id, payload)
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist not found",
        ) from exc
