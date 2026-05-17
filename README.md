# BirthSync Mini App Backend

Backend API for the BirthSync gift recommendation service.

## Stack

- Python 3.12
- FastAPI
- Pydantic
- asyncpg
- PostgreSQL

## Local Run

### Docker

1. Create `.env` from `.env.example`.

```bash
cp .env.example .env
```

2. Start the API and PostgreSQL:

```bash
docker compose up -d --build
```

3. Open API docs:

```text
http://127.0.0.1:8000/docs
```

Useful commands:

```bash
docker compose logs -f api
docker compose down
docker compose down -v
```

For Ubuntu 20.04 with legacy Compose, use `docker-compose` instead of `docker compose`.

## Frontend API

Frontend routes use the `/api` prefix and camelCase JSON fields. Requests must pass the current Telegram user id in a header:

```http
X-Telegram-Id: 435918797
```

Optional headers for first user sync:

```http
X-Telegram-Handle: akulovroma
X-First-Name: Roman
X-Last-Name: Akulov
```

Production Telegram Mini App requests may additionally pass signed launch data:

```http
X-Telegram-Init-Data: query_id=...&user=...&auth_date=...&hash=...
```

If `TELEGRAM_BOT_TOKEN` is configured, the backend verifies `X-Telegram-Init-Data` and rejects identity mismatches.

Implemented endpoints:

```text
GET    /api/auth/me
PATCH  /api/auth/profile

GET    /api/settings
PATCH  /api/settings

GET    /api/contacts
POST   /api/contacts
GET    /api/contacts/{contactId}
PATCH  /api/contacts/{contactId}
DELETE /api/contacts/{contactId}

GET    /api/contacts/{contactId}/notes
POST   /api/contacts/{contactId}/notes
PATCH  /api/contacts/{contactId}/notes/{noteId}
DELETE /api/contacts/{contactId}/notes/{noteId}

GET    /api/contacts/{contactId}/widgets
POST   /api/contacts/{contactId}/widgets
PATCH  /api/contacts/{contactId}/widgets/{widgetId}
DELETE /api/contacts/{contactId}/widgets/{widgetId}

GET    /api/contacts/{contactId}/recommendations
POST   /api/contacts/{contactId}/recommendations

GET    /api/reminders
POST   /api/reminders
PATCH  /api/reminders/{reminderId}
DELETE /api/reminders/{reminderId}
```

Example:

```bash
curl -H "X-Telegram-Id: 435918797" http://127.0.0.1:8000/api/auth/me
```

Gift recommendations are generated through GigaChat and saved in PostgreSQL:

```bash
curl -X POST "http://127.0.0.1:8000/api/contacts/{contactId}/recommendations" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Id: 435918797" \
  -d '{
    "categories": ["music", "concerts", "home comfort"],
    "notes": "Likes practical gifts",
    "saveAsWidgets": false
  }'
```

Required GigaChat environment variables:

```env
CREDENTIALS=your_gigachat_credentials
GIGACHAT_MODEL=GigaChat-Pro
GIGACHAT_VERIFY_SSL_CERTS=false
```

Logging is configured through environment variables:

```env
LOG_LEVEL=INFO
LOG_JSON=false
```

Use `LOG_JSON=true` on the server if logs are collected by an external system.

Telegram initData verification is configured through:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_INIT_DATA_MAX_AGE_SECONDS=86400
```

Frontend contract details:

- `DELETE` endpoints return `204 No Content`.
- Missing `X-Telegram-Id` returns `400 Bad Request`.
- Widget accents are `gray`, `red`, `blue`, `green`, `yellow`, `purple`.
- Reminders support `repeat`, `earlyReminderMinutes`, and `earlyReminderRepeat`.
- User settings are persisted through `/api/settings`.

For frontend deployments, add their exact origins to `CORS_ORIGINS`:

```env
CORS_ORIGINS=["https://birthsync.ru","https://www.birthsync.ru","https://birthsync-app-git-backend-integration-falcion-io.vercel.app"]
```

For temporary Vercel preview builds, a regex can be used instead:

```env
CORS_ORIGIN_REGEX=^https://birthsync-app.*\.vercel\.app$
```

### Without API Container

1. Create `.env` from `.env.example` and set database variables:

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=birthsync
DB_PASS=birthsync
DB_NAME=birthsync
```

2. Start PostgreSQL:

```bash
docker compose up -d postgres
```

3. Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

4. Apply the SQL schema:

```bash
.venv/bin/python -m scripts.init_db
```

For local development, schema initialization can also be enabled with:

```env
DB_APPLY_SCHEMA_ON_STARTUP=true
```

5. Start the API:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Server Run

1. Install Docker and Docker Compose on the server.
2. Copy the project to the server.
3. Create `.env` from `.env.example`.
4. Use strong database credentials in `.env`.
5. Add `CREDENTIALS` for GigaChat recommendations.
6. Start services:

```bash
docker compose up -d --build
```

The API will be available on port `8000`. For public access, put Nginx in front of it and proxy HTTPS traffic to `127.0.0.1:8000`.
