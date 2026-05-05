import asyncpg
from fastapi import APIRouter, HTTPException, status

from app import repositories, schemas

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(payload: schemas.CategoryCreate):
    try:
        return await repositories.create_category(payload)
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not exist",
        ) from exc
