import asyncpg
from fastapi import APIRouter, HTTPException, status

from app import repositories, schemas

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("", response_model=schemas.ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(payload: schemas.ContactCreate):
    try:
        return await repositories.create_contact(payload)
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner user or contact user does not exist",
        ) from exc
