from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
from loguru import logger

from app.db.pool import get_db_pool


@asynccontextmanager
async def db_connection() -> AsyncIterator[asyncpg.Connection]:
    try:
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            yield conn
    except Exception as exc:
        logger.exception(f"Error acquiring connection: {exc}")
        raise


@asynccontextmanager
async def db_transaction() -> AsyncIterator[asyncpg.Connection]:
    try:
        async with db_connection() as conn:
            async with conn.transaction():
                yield conn
    except Exception as exc:
        logger.exception(f"Error during transaction: {exc}")
        raise
