import json
from datetime import date
from typing import Any
from uuid import UUID

import asyncpg

from app import frontend_schemas as schemas
from app.db.context import db_connection, db_transaction


def _decode_links(value: Any) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, str):
        return json.loads(value)
    return value


def _user_row(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["telegram_id"]),
        "telegram_id": row["telegram_id"],
        "telegram_handle": row["username"],
        "first_name": row["first_name"] or row["username"] or "User",
        "last_name": row["last_name"],
        "birth_date": row["birth_date"],
        "phone": row["phone"],
        "email": row["email"],
        "profile_image": row["profile_image"],
        "common_notes": row["common_notes"],
        "preferred_language": row["preferred_language"] or "ru",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _contact_row(row: asyncpg.Record, additional_notes: list[str] | None = None) -> dict:
    return {
        "id": row["public_id"],
        "name": row["display_name"],
        "relation": row["relation"],
        "telegram_handle": row["telegram_handle"],
        "birth_date": row["birth_date"],
        "phone": row["phone"],
        "email": row["email"],
        "profile_image": row["profile_image"],
        "common_notes": row["common_notes"],
        "additional_notes": additional_notes or [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "is_archived": row["is_archived"],
    }


def _note_row(row: asyncpg.Record) -> dict:
    return {
        "id": row["id"],
        "contact_id": row["contact_public_id"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _widget_row(row: asyncpg.Record) -> dict:
    return {
        "id": row["id"],
        "contact_id": row["contact_public_id"],
        "title": row["title"],
        "description": row["description"],
        "image_url": row["image_url"],
        "price": row["price"],
        "links": _decode_links(row["links"]),
        "accent": row["accent"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _reminder_row(row: asyncpg.Record) -> dict:
    return {
        "id": row["id"],
        "contact_id": row["contact_public_id"],
        "title": row["title"],
        "description": row["description"],
        "date": row["reminder_date"],
        "time": row["reminder_time"],
        "completed": row["completed"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def get_or_create_user(
    telegram_id: int,
    telegram_handle: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    query = """
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (telegram_id) DO UPDATE
        SET username = COALESCE(EXCLUDED.username, users.username),
            first_name = COALESCE(EXCLUDED.first_name, users.first_name),
            last_name = COALESCE(EXCLUDED.last_name, users.last_name),
            updated_at = now()
        RETURNING id, telegram_id, username, first_name, last_name, birth_date,
            phone, email, profile_image, common_notes, preferred_language,
            created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, telegram_id, telegram_handle, first_name, last_name)
    return _user_row(row)


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    query = """
        SELECT id, telegram_id, username, first_name, last_name, birth_date,
            phone, email, profile_image, common_notes, preferred_language,
            created_at, updated_at
        FROM users
        WHERE telegram_id = $1
    """
    async with db_connection() as conn:
        row = await conn.fetchrow(query, telegram_id)
    return _user_row(row) if row else None


async def patch_user_profile(telegram_id: int, payload: schemas.CurrentUserPatch) -> dict | None:
    data = payload.model_dump(exclude_unset=True)
    if "telegram_handle" in data:
        data["username"] = data.pop("telegram_handle")

    allowed = [
        "username",
        "first_name",
        "last_name",
        "birth_date",
        "phone",
        "email",
        "profile_image",
        "common_notes",
        "preferred_language",
    ]
    assignments = [f"{field} = ${idx}" for idx, field in enumerate(data, start=1) if field in allowed]
    if not assignments:
        return await get_user_by_telegram_id(telegram_id)

    values = [data[field] for field in data if field in allowed]
    query = f"""
        UPDATE users
        SET {", ".join(assignments)}, updated_at = now()
        WHERE telegram_id = ${len(values) + 1}
        RETURNING id, telegram_id, username, first_name, last_name, birth_date,
            phone, email, profile_image, common_notes, preferred_language,
            created_at, updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, *values, telegram_id)
    return _user_row(row) if row else None


async def _get_user_internal_id(conn: asyncpg.Connection, telegram_id: int) -> int | None:
    return await conn.fetchval("SELECT id FROM users WHERE telegram_id = $1", telegram_id)


async def _get_contact_internal_id(
    conn: asyncpg.Connection,
    owner_user_id: int,
    contact_public_id: UUID,
) -> int | None:
    return await conn.fetchval(
        """
        SELECT id
        FROM contacts
        WHERE owner_user_id = $1 AND public_id = $2
        """,
        owner_user_id,
        contact_public_id,
    )


async def create_contact(telegram_id: int, payload: schemas.ContactCreate) -> dict:
    query = """
        INSERT INTO contacts (
            owner_user_id, display_name, relation, telegram_handle, birth_date, phone, email,
            profile_image, common_notes, status
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'confirmed')
        RETURNING public_id, display_name, relation, birth_date, phone, email,
            profile_image, common_notes, is_archived, created_at, updated_at,
            telegram_handle
    """
    async with db_transaction() as conn:
        owner_user_id = await _get_user_internal_id(conn, telegram_id)
        row = await conn.fetchrow(
            query,
            owner_user_id,
            payload.name,
            payload.relation,
            payload.telegram_handle,
            payload.birth_date,
            payload.phone,
            payload.email,
            payload.profile_image,
            payload.common_notes,
        )
    return _contact_row(row)


async def list_contacts(telegram_id: int, include_archived: bool = False) -> list[dict]:
    query = """
        SELECT c.public_id, c.display_name, c.relation, c.birth_date, c.phone, c.email,
            c.profile_image, c.common_notes, c.is_archived, c.created_at, c.updated_at,
            c.telegram_handle,
            COALESCE(array_agg(n.id::text) FILTER (WHERE n.id IS NOT NULL), '{}') AS note_ids
        FROM contacts c
        JOIN users owner ON owner.id = c.owner_user_id
        LEFT JOIN contact_notes n ON n.contact_id = c.id
        WHERE owner.telegram_id = $1
            AND ($2::boolean OR c.is_archived = false)
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, telegram_id, include_archived)
    return [_contact_row(row, list(row["note_ids"])) for row in rows]


async def get_contact(telegram_id: int, contact_public_id: UUID) -> dict | None:
    query = """
        SELECT c.public_id, c.display_name, c.relation, c.birth_date, c.phone, c.email,
            c.profile_image, c.common_notes, c.is_archived, c.created_at, c.updated_at,
            c.telegram_handle,
            COALESCE(array_agg(n.id::text) FILTER (WHERE n.id IS NOT NULL), '{}') AS note_ids
        FROM contacts c
        JOIN users owner ON owner.id = c.owner_user_id
        LEFT JOIN contact_notes n ON n.contact_id = c.id
        WHERE owner.telegram_id = $1 AND c.public_id = $2
        GROUP BY c.id
    """
    async with db_connection() as conn:
        row = await conn.fetchrow(query, telegram_id, contact_public_id)
    return _contact_row(row, list(row["note_ids"])) if row else None


async def patch_contact(
    telegram_id: int,
    contact_public_id: UUID,
    payload: schemas.ContactPatch,
) -> dict | None:
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        data["display_name"] = data.pop("name")

    allowed = [
        "display_name",
        "relation",
        "telegram_handle",
        "birth_date",
        "phone",
        "email",
        "profile_image",
        "common_notes",
        "is_archived",
    ]
    values = [data[field] for field in data if field in allowed]
    if not values:
        return await get_contact(telegram_id, contact_public_id)

    assignments = [f"{field} = ${idx + 2}" for idx, field in enumerate(data) if field in allowed]
    query = f"""
        UPDATE contacts c
        SET {", ".join(assignments)}, updated_at = now()
        FROM users owner
        WHERE c.owner_user_id = owner.id
            AND owner.telegram_id = $1
            AND c.public_id = ${len(values) + 2}
        RETURNING c.public_id, c.display_name, c.relation, c.birth_date, c.phone, c.email,
            c.profile_image, c.common_notes, c.is_archived, c.created_at, c.updated_at,
            c.telegram_handle
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, telegram_id, *values, contact_public_id)
    return _contact_row(row) if row else None


async def archive_contact(telegram_id: int, contact_public_id: UUID) -> bool:
    query = """
        UPDATE contacts c
        SET is_archived = true, updated_at = now()
        FROM users owner
        WHERE c.owner_user_id = owner.id
            AND owner.telegram_id = $1
            AND c.public_id = $2
    """
    async with db_transaction() as conn:
        result = await conn.execute(query, telegram_id, contact_public_id)
    return result == "UPDATE 1"


async def create_note(telegram_id: int, contact_public_id: UUID, payload: schemas.NoteCreate) -> dict | None:
    query = """
        INSERT INTO contact_notes (contact_id, title, content)
        VALUES ($1, $2, $3)
        RETURNING id, $4::uuid AS contact_public_id, title, content, created_at, updated_at
    """
    async with db_transaction() as conn:
        owner_user_id = await _get_user_internal_id(conn, telegram_id)
        contact_id = await _get_contact_internal_id(conn, owner_user_id, contact_public_id)
        if contact_id is None:
            return None
        row = await conn.fetchrow(query, contact_id, payload.title, payload.content, contact_public_id)
    return _note_row(row)


async def list_notes(telegram_id: int, contact_public_id: UUID) -> list[dict] | None:
    query = """
        SELECT n.id, c.public_id AS contact_public_id, n.title, n.content, n.created_at, n.updated_at
        FROM contact_notes n
        JOIN contacts c ON c.id = n.contact_id
        JOIN users owner ON owner.id = c.owner_user_id
        WHERE owner.telegram_id = $1 AND c.public_id = $2
        ORDER BY n.created_at DESC
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, telegram_id, contact_public_id)
    return [_note_row(row) for row in rows]


async def patch_note(
    telegram_id: int,
    contact_public_id: UUID,
    note_id: UUID,
    payload: schemas.NotePatch,
) -> dict | None:
    data = payload.model_dump(exclude_unset=True)
    allowed = ["title", "content"]
    values = [data[field] for field in data if field in allowed]
    if not values:
        return None
    assignments = [f"n.{field} = ${idx + 3}" for idx, field in enumerate(data) if field in allowed]
    query = f"""
        UPDATE contact_notes n
        SET {", ".join(assignments)}, updated_at = now()
        FROM contacts c
        JOIN users owner ON owner.id = c.owner_user_id
        WHERE n.contact_id = c.id
            AND owner.telegram_id = $1
            AND c.public_id = $2
            AND n.id = ${len(values) + 3}
        RETURNING n.id, c.public_id AS contact_public_id, n.title, n.content, n.created_at, n.updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, telegram_id, contact_public_id, *values, note_id)
    return _note_row(row) if row else None


async def delete_note(telegram_id: int, contact_public_id: UUID, note_id: UUID) -> bool:
    query = """
        DELETE FROM contact_notes n
        USING contacts c, users owner
        WHERE n.contact_id = c.id
            AND owner.id = c.owner_user_id
            AND owner.telegram_id = $1
            AND c.public_id = $2
            AND n.id = $3
    """
    async with db_transaction() as conn:
        result = await conn.execute(query, telegram_id, contact_public_id, note_id)
    return result == "DELETE 1"


async def create_widget(telegram_id: int, contact_public_id: UUID, payload: schemas.WidgetCreate) -> dict | None:
    query = """
        INSERT INTO contact_widgets (contact_id, title, description, image_url, price, links, accent)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
        RETURNING id, $8::uuid AS contact_public_id, title, description, image_url,
            price, links, accent, created_at, updated_at
    """
    async with db_transaction() as conn:
        owner_user_id = await _get_user_internal_id(conn, telegram_id)
        contact_id = await _get_contact_internal_id(conn, owner_user_id, contact_public_id)
        if contact_id is None:
            return None
        row = await conn.fetchrow(
            query,
            contact_id,
            payload.title,
            payload.description,
            payload.image_url,
            payload.price,
            json.dumps([link.model_dump() for link in payload.links]),
            payload.accent,
            contact_public_id,
        )
    return _widget_row(row)


async def list_widgets(telegram_id: int, contact_public_id: UUID) -> list[dict]:
    query = """
        SELECT w.id, c.public_id AS contact_public_id, w.title, w.description,
            w.image_url, w.price, w.links, w.accent, w.created_at, w.updated_at
        FROM contact_widgets w
        JOIN contacts c ON c.id = w.contact_id
        JOIN users owner ON owner.id = c.owner_user_id
        WHERE owner.telegram_id = $1 AND c.public_id = $2
        ORDER BY w.created_at DESC
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, telegram_id, contact_public_id)
    return [_widget_row(row) for row in rows]


async def patch_widget(
    telegram_id: int,
    contact_public_id: UUID,
    widget_id: UUID,
    payload: schemas.WidgetPatch,
) -> dict | None:
    data = payload.model_dump(exclude_unset=True)
    if "links" in data and data["links"] is not None:
        data["links"] = json.dumps(data["links"])
    allowed = ["title", "description", "image_url", "price", "links", "accent"]
    values = [data[field] for field in data if field in allowed]
    if not values:
        return None
    assignments = [
        f"w.{field} = ${idx + 3}::jsonb" if field == "links" else f"w.{field} = ${idx + 3}"
        for idx, field in enumerate(data)
        if field in allowed
    ]
    query = f"""
        UPDATE contact_widgets w
        SET {", ".join(assignments)}, updated_at = now()
        FROM contacts c
        JOIN users owner ON owner.id = c.owner_user_id
        WHERE w.contact_id = c.id
            AND owner.telegram_id = $1
            AND c.public_id = $2
            AND w.id = ${len(values) + 3}
        RETURNING w.id, c.public_id AS contact_public_id, w.title, w.description,
            w.image_url, w.price, w.links, w.accent, w.created_at, w.updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, telegram_id, contact_public_id, *values, widget_id)
    return _widget_row(row) if row else None


async def delete_widget(telegram_id: int, contact_public_id: UUID, widget_id: UUID) -> bool:
    query = """
        DELETE FROM contact_widgets w
        USING contacts c, users owner
        WHERE w.contact_id = c.id
            AND owner.id = c.owner_user_id
            AND owner.telegram_id = $1
            AND c.public_id = $2
            AND w.id = $3
    """
    async with db_transaction() as conn:
        result = await conn.execute(query, telegram_id, contact_public_id, widget_id)
    return result == "DELETE 1"


async def create_reminder(telegram_id: int, payload: schemas.ReminderCreate) -> dict | None:
    query = """
        INSERT INTO reminders (contact_id, title, description, reminder_date, reminder_time, completed)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, $7::uuid AS contact_public_id, title, description, reminder_date,
            reminder_time, completed, created_at, updated_at
    """
    async with db_transaction() as conn:
        owner_user_id = await _get_user_internal_id(conn, telegram_id)
        contact_id = await _get_contact_internal_id(conn, owner_user_id, payload.contact_id)
        if contact_id is None:
            return None
        row = await conn.fetchrow(
            query,
            contact_id,
            payload.title,
            payload.description,
            payload.date,
            payload.time,
            payload.completed,
            payload.contact_id,
        )
    return _reminder_row(row)


async def list_reminders(
    telegram_id: int,
    contact_public_id: UUID | None = None,
    upcoming: bool = False,
) -> list[dict]:
    today = date.today()
    query = """
        SELECT r.id, c.public_id AS contact_public_id, r.title, r.description,
            r.reminder_date, r.reminder_time, r.completed, r.created_at, r.updated_at
        FROM reminders r
        JOIN contacts c ON c.id = r.contact_id
        JOIN users owner ON owner.id = c.owner_user_id
        WHERE owner.telegram_id = $1
            AND ($2::uuid IS NULL OR c.public_id = $2)
            AND ($3::boolean = false OR r.reminder_date >= $4)
        ORDER BY r.reminder_date ASC, r.reminder_time ASC NULLS LAST
    """
    async with db_connection() as conn:
        rows = await conn.fetch(query, telegram_id, contact_public_id, upcoming, today)
    return [_reminder_row(row) for row in rows]


async def patch_reminder(telegram_id: int, reminder_id: UUID, payload: schemas.ReminderPatch) -> dict | None:
    data = payload.model_dump(exclude_unset=True)
    if "date" in data:
        data["reminder_date"] = data.pop("date")
    if "time" in data:
        data["reminder_time"] = data.pop("time")
    allowed = ["title", "description", "reminder_date", "reminder_time", "completed"]
    values = [data[field] for field in data if field in allowed]
    if not values:
        return None
    assignments = [f"r.{field} = ${idx + 2}" for idx, field in enumerate(data) if field in allowed]
    query = f"""
        UPDATE reminders r
        SET {", ".join(assignments)}, updated_at = now()
        FROM contacts c
        JOIN users owner ON owner.id = c.owner_user_id
        WHERE r.contact_id = c.id
            AND owner.telegram_id = $1
            AND r.id = ${len(values) + 2}
        RETURNING r.id, c.public_id AS contact_public_id, r.title, r.description,
            r.reminder_date, r.reminder_time, r.completed, r.created_at, r.updated_at
    """
    async with db_transaction() as conn:
        row = await conn.fetchrow(query, telegram_id, *values, reminder_id)
    return _reminder_row(row) if row else None


async def delete_reminder(telegram_id: int, reminder_id: UUID) -> bool:
    query = """
        DELETE FROM reminders r
        USING contacts c, users owner
        WHERE r.contact_id = c.id
            AND owner.id = c.owner_user_id
            AND owner.telegram_id = $1
            AND r.id = $2
    """
    async with db_transaction() as conn:
        result = await conn.execute(query, telegram_id, reminder_id)
    return result == "DELETE 1"
