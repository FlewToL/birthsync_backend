import asyncpg

from app import schemas
from app.db.context import db_connection, db_transaction


def _row_to_dict(row: asyncpg.Record | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


async def create_user(payload: schemas.UserCreate) -> dict:
    query = """
        INSERT INTO users (telegram_id, username)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO UPDATE
        SET username = EXCLUDED.username,
            updated_at = now()
        RETURNING id, telegram_id, username, created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, payload.telegram_id, payload.username)
    return dict(row)


async def get_user(user_id: int) -> dict | None:
    query = """
        SELECT id, telegram_id, username, created_at, updated_at
        FROM users
        WHERE id = $1
    """
    async with db_connection() as conn:
        row = await conn.fetchrow(query, user_id)
    return _row_to_dict(row)


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    query = """
        SELECT id, telegram_id, username, created_at, updated_at
        FROM users
        WHERE telegram_id = $1
    """
    async with db_connection() as conn:
        row = await conn.fetchrow(query, telegram_id)
    return _row_to_dict(row)


async def upsert_user_card(
    user_id: int,
    payload: schemas.UserCardUpsert,
) -> dict:
    query = """
        INSERT INTO user_cards (user_id, first_name, last_name, birth_date, about)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id) DO UPDATE
        SET first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            birth_date = EXCLUDED.birth_date,
            about = EXCLUDED.about,
            updated_at = now()
        RETURNING user_id, first_name, last_name, birth_date, about, created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(
            query,
            user_id,
            payload.first_name,
            payload.last_name,
            payload.birth_date,
            payload.about,
        )
    return dict(row)


async def get_user_card(user_id: int) -> dict | None:
    query = """
        SELECT user_id, first_name, last_name, birth_date, about, created_at, updated_at
        FROM user_cards
        WHERE user_id = $1
    """
    async with db_connection() as conn:
        row = await conn.fetchrow(query, user_id)
    return _row_to_dict(row)


async def create_contact(payload: schemas.ContactCreate) -> dict:
    query = """
        INSERT INTO contacts (
            owner_user_id,
            contact_user_id,
            display_name,
            relation,
            birth_date,
            status
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, owner_user_id, contact_user_id, display_name, relation,
            birth_date, status, created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(
            query,
            payload.owner_user_id,
            payload.contact_user_id,
            payload.display_name,
            payload.relation,
            payload.birth_date,
            payload.status,
        )
    return dict(row)


async def list_contacts(user_id: int) -> list[dict]:
    query = """
        SELECT id, owner_user_id, contact_user_id, display_name, relation,
            birth_date, status, created_at, updated_at
        FROM contacts
        WHERE owner_user_id = $1
        ORDER BY created_at DESC
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, user_id)
    return [dict(row) for row in rows]


async def create_category(payload: schemas.CategoryCreate) -> dict:
    query = """
        INSERT INTO user_categories (user_id, name)
        VALUES ($1, $2)
        ON CONFLICT (user_id, name) DO UPDATE
        SET name = EXCLUDED.name
        RETURNING id, user_id, name, created_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, payload.user_id, payload.name)
    return dict(row)


async def list_categories(user_id: int) -> list[dict]:
    query = """
        SELECT id, user_id, name, created_at
        FROM user_categories
        WHERE user_id = $1
        ORDER BY name
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, user_id)
    return [dict(row) for row in rows]


async def create_wishlist(payload: schemas.WishlistCreate) -> dict:
    query = """
        INSERT INTO wishlists (owner_user_id, contact_id, title, description)
        VALUES ($1, $2, $3, $4)
        RETURNING id, owner_user_id, contact_id, title, description, created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(
            query,
            payload.owner_user_id,
            payload.contact_id,
            payload.title,
            payload.description,
        )
    return dict(row)


async def list_wishlists(user_id: int) -> list[dict]:
    query = """
        SELECT id, owner_user_id, contact_id, title, description, created_at, updated_at
        FROM wishlists
        WHERE owner_user_id = $1
        ORDER BY created_at DESC
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, user_id)
    return [dict(row) for row in rows]


async def create_wishlist_item(
    wishlist_id: int,
    payload: schemas.WishlistItemCreate,
) -> dict:
    query = """
        INSERT INTO wishlist_items (wishlist_id, title, description, url)
        VALUES ($1, $2, $3, $4)
        RETURNING id, wishlist_id, title, description, url, status, created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(
            query,
            wishlist_id,
            payload.title,
            payload.description,
            payload.url,
        )
    return dict(row)


async def list_wishlist_items(wishlist_id: int) -> list[dict]:
    query = """
        SELECT id, wishlist_id, title, description, url, status, created_at, updated_at
        FROM wishlist_items
        WHERE wishlist_id = $1
        ORDER BY created_at DESC
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, wishlist_id)
    return [dict(row) for row in rows]
