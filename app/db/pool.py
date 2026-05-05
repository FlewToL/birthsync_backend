from pathlib import Path

import asyncpg
from loguru import logger

from app.core.config import settings

db_pool: asyncpg.Pool | None = None


@logger.catch()
async def init_connection(conn: asyncpg.Connection) -> None:
    try:
        await conn.execute("SET statement_timeout = 5000")
        await conn.execute("SET lock_timeout = 5000")
        logger.debug("Database timeouts configured")
    except Exception as exc:
        logger.error(f"Failed to configure database timeouts: {exc}")
        raise


async def init_db_pool() -> None:
    global db_pool

    if db_pool is not None:
        return

    try:
        logger.info(
            f"Creating database pool for {settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )
        db_pool = await asyncpg.create_pool(
            user=settings.db_user,
            password=settings.db_pass.get_secret_value(),
            database=settings.db_name,
            host=settings.db_host,
            port=settings.db_port,
            min_size=1,
            max_size=100,
            init=init_connection,
            command_timeout=30,
        )
        logger.success("Database pool successfully created")
    except Exception as exc:
        logger.error(f"Failed to create database pool: {exc}")
        raise


async def close_db_pool() -> None:
    global db_pool

    if db_pool is not None:
        await db_pool.close()
        db_pool = None
        logger.success("Database pool successfully closed")


async def get_db_pool() -> asyncpg.Pool:
    if db_pool is None:
        await init_db_pool()

    if db_pool is None:
        raise RuntimeError("Database pool is not initialized")

    return db_pool


async def create_db_pool() -> asyncpg.Pool:
    await init_db_pool()
    return await get_db_pool()


async def init_schema(pool: asyncpg.Pool | None = None) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    sql = schema_path.read_text(encoding="utf-8")
    db = pool or await get_db_pool()
    async with db.acquire() as conn:
        await conn.execute(sql)
    logger.success("Database schema initialized")
