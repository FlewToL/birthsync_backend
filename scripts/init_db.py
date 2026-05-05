import asyncio

from app.db.pool import close_db_pool, init_db_pool, init_schema


async def main() -> None:
    await init_db_pool()
    try:
        await init_schema()
    finally:
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
