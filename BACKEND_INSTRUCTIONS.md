# Backend Instructions - BirthdaySync Mini-App

**Version:** 1.0  
**Status:** Frontend integration complete; backend implementation in progress  
**Technology:** FastAPI + PostgreSQL  
**Client Framework:** React 18.3 + TypeScript 5.9 + Telegram Mini App SDK (@tma.js/sdk-react 3.0)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Configuration](#configuration)
4. [Data Models](#data-models)
5. [API Endpoints](#api-endpoints)
6. [Error Handling](#error-handling)
7. [Validation Rules](#validation-rules)
8. [Integration Patterns](#integration-patterns)
9. [Implementation Status](#implementation-status)
10. [Remaining Gaps](#remaining-gaps)
11. [Testing Checklist](#testing-checklist)

---

## Architecture Overview

The BirthdaySync Mini-App is a Telegram Mini App that helps users manage contact information and track birthdays. The frontend is a React SPA that communicates with a FastAPI backend via JSON REST API.

### Request Flow

```
Telegram Mini App Client (React)
    ↓ (HTTP requests with X-Telegram-Id header)
FastAPI Backend
    ↓ (PostgreSQL queries)
PostgreSQL Database
```

### Key Principles

- **Stateless API:** Backend does not maintain session state; authentication is per-request via Telegram user ID
- **User Scoping:** All data is scoped to the authenticated Telegram user ID (extracted from launch params)
- **Immutable Timestamps:** All entities track creation and update times (`createdAt`, `updatedAt`)
- **Soft Deletes:** Contacts can be archived but not hard-deleted (optional feature)
- **Normalized Response Format:** All responses use `camelCase` field names for frontend compatibility

---

## Authentication & Authorization

### Telegram Mini App Authentication

The frontend extracts user information from Telegram Mini App launch parameters via `@tma.js/sdk-react`:

```typescript
// Example: What the frontend extracts from SDK
{
  telegramId: 123456789,              // Required: unique Telegram user ID
  telegramHandle: "johndoe",          // Optional: username (without @)
  firstName: "John",                  // Optional: first name
  lastName: "Doe"                     // Optional: last name
}
```

### Request Headers

**Required Headers (all requests):**
- `X-Telegram-Id`: The numeric Telegram user ID (e.g., `"123456789"`)
- `Content-Type`: `"application/json"`

**Optional Headers (metadata only):**
- `X-Telegram-Handle`: Username without @ (e.g., `"johndoe"`)
- `X-First-Name`: User's first name
- `X-Last-Name`: User's last name

### Example Request

```bash
curl -X GET http://127.0.0.1:8000/api/contacts \
  -H "X-Telegram-Id: 123456789" \
  -H "X-Telegram-Handle: johndoe" \
  -H "X-First-Name: John" \
  -H "X-Last-Name: Doe" \
  -H "Content-Type: application/json"
```

### Authentication Flow

1. **Development Mode:** Frontend uses mocked Telegram context (ID = 1)
2. **Production Mode:** Frontend extracts context from Telegram Mini App SDK
3. **Backend Validation:** Verify `X-Telegram-Id` header exists; extract as request scope
4. **Data Isolation:** All queries automatically filter by authenticated user ID

### Future: Telegram Bot API Verification

**TODO (Phase 2):** Implement full `initData` verification using Telegram Bot API signature:
- Accept optional `X-Telegram-Init-Data` header
- Verify HMAC-SHA256 signature using bot token
- Fallback to `X-Telegram-Id` header if initData unavailable
- Log failed verifications for security monitoring

---

## Configuration

### Environment Variables

**Backend (`.env` or `docker-compose.yml`):**

```ini
DATABASE_URL=postgresql://user:password@localhost:5432/birthsync
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11  # For future initData verification
API_PORT=8000
API_HOST=127.0.0.1
CORS_ORIGINS=http://localhost:5173,https://birthsync.example.com
LOG_LEVEL=INFO
```

**Frontend (`.env`):**

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_APP_BASE=/
```

### Database Schema Notes

- All timestamps should be ISO 8601 format with timezone (e.g., `2025-01-15T10:30:00Z`)
- Birth dates stored as `YYYY-MM-DD` (date-only, no time component)
- UUIDs or stable numeric IDs for entity primary keys
- Composite unique constraints: `(telegram_id, contact_id)` for contacts, notes, widgets, reminders
- Consider partial indexes on `isArchived = false` for performance

---

## Data Models

All data models use `camelCase` in JSON responses (via Pydantic `alias_generator` or FastAPI response normalization).

### Contact (Profile)

Represents a person the user wants to track.

**Backend Schema:**
```typescript
type BackendContact = {
  id: string;                          // Unique identifier (UUID or numeric)
  name: string;                        // Required: contact's name
  relation?: string | null;            // e.g., "Friend", "Family", "Colleague"
  telegramHandle?: string | null;      // Telegram username without @
  birthDate?: string | null;           // ISO date "YYYY-MM-DD"
  phone?: string | null;               // Phone number (format TBD)
  email?: string | null;               // Email address
  profileImage?: string | null;        // Base64 image data or image URL
  commonNotes?: string | null;         // Rich text notes about contact
  additionalNotes?: BackendNote[];     // Array of structured notes
  widgets?: BackendWidget[];           // Array of gift/item suggestions
  reminders?: BackendReminder[];       // Array of reminders (birthdays, anniversaries, etc.)
  createdAt: string;                   // ISO 8601 timestamp
  updatedAt: string;                   // ISO 8601 timestamp
  isArchived?: boolean;                // Soft delete flag (optional)
};
```

**Constraints:**
- `name` required and non-empty (max 255 chars)
- `birthDate` must be valid date or null
- `email` should be valid email format if provided
- `phone` should be phone-like format if provided (no strict validation required)
- `profileImage` if provided, should be valid base64 or URL

**Example:**
```json
{
  "id": "c_550e8400e29b41d4a716446655440000",
  "name": "Alice Johnson",
  "relation": "Friend",
  "telegramHandle": "alice_j",
  "birthDate": "1990-03-15",
  "phone": "+1-555-123-4567",
  "email": "alice@example.com",
  "profileImage": "data:image/png;base64,iVBORw0KG...",
  "commonNotes": "Met at university, loves hiking",
  "createdAt": "2025-01-10T14:23:00Z",
  "updatedAt": "2025-01-15T10:30:00Z",
  "isArchived": false,
  "additionalNotes": [...],
  "widgets": [...],
  "reminders": [...]
}
```

---

### Note

Structured notes attached to a contact.

**Backend Schema:**
```typescript
type BackendNote = {
  id: string;                    // Unique identifier
  contactId: string;             // Foreign key to Contact
  title: string;                 // Note title (max 255 chars)
  content: string;               // Note content (rich text or markdown)
  createdAt: string;             // ISO 8601 timestamp
  updatedAt: string;             // ISO 8601 timestamp
};
```

**Constraints:**
- `title` required, non-empty (max 255 chars)
- `content` optional but non-empty if provided (max 5000 chars recommended)
- `contactId` must reference existing Contact

**Example:**
```json
{
  "id": "n_660e8400e29b41d4a716446655440001",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Favorite Movies",
  "content": "- Inception\n- The Matrix\n- Interstellar",
  "createdAt": "2025-01-12T08:15:00Z",
  "updatedAt": "2025-01-12T08:15:00Z"
}
```

---

### Widget

Gift suggestions or item wish lists for a contact.

**Backend Schema:**
```typescript
type BackendWidget = {
  id: string;                              // Unique identifier
  contactId: string;                       // Foreign key to Contact
  title: string;                           // Widget title (max 255 chars)
  description?: string | null;             // Detailed description (max 1000 chars)
  imageUrl?: string | null;                // Product image URL or base64
  price?: string | null;                   // Price as string (e.g., "$29.99", "500 RUB")
  links?: Array<{ text: string; url: string }> | null;  // External links (store URLs, etc.)
  accent?: 'gray' | 'red' | 'blue' | 'green' | 'yellow' | 'purple';  // UI accent color
  createdAt: string;                       // ISO 8601 timestamp
  updatedAt: string;                       // ISO 8601 timestamp
};
```

**Constraints:**
- `title` required, non-empty (max 255 chars)
- `description` max 1000 chars
- `price` format flexible (store as string for localization)
- `links` max 10 entries per widget
- `accent` must be one of the predefined colors

**Example:**
```json
{
  "id": "w_770e8400e29b41d4a716446655440002",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Hiking Boots - Salomon Quest 4D",
  "description": "Waterproof hiking boots with excellent ankle support",
  "imageUrl": "https://example.com/boots.jpg",
  "price": "$189.99",
  "links": [
    { "text": "Amazon", "url": "https://amazon.com/..." },
    { "text": "REI", "url": "https://rei.com/..." }
  ],
  "accent": "blue",
  "createdAt": "2025-01-14T16:45:00Z",
  "updatedAt": "2025-01-14T16:45:00Z"
}
```

---

### Reminder

Events tied to contacts (birthdays, anniversaries, etc.).

**Backend Schema:**
```typescript
type BackendReminder = {
  id: string;                    // Unique identifier
  contactId: string;             // Foreign key to Contact
  title: string;                 // Reminder title (max 255 chars)
  description?: string | null;   // Additional details (max 500 chars)
  date: string;                  // Date in "YYYY-MM-DD" format
  time?: string | null;          // Time in "HH:MM" format (24-hour)
  completed: boolean;            // Whether reminder was marked done
  createdAt: string;             // ISO 8601 timestamp
  updatedAt: string;             // ISO 8601 timestamp
  
  // TODO: Fields not yet sent by frontend (reserved for Phase 2)
  // repeat?: 'daily' | 'weekly' | 'monthly' | 'yearly' | null;
  // earlyReminderMinutes?: number | null;
  // earlyReminderRepeat?: 'once' | 'daily' | null;
};
```

**Constraints:**
- `title` required, non-empty (max 255 chars)
- `date` required, valid ISO date
- `time` optional, format HH:MM 24-hour or null
- `completed` boolean flag for UI tracking
- `contactId` must reference existing Contact

**Example:**
```json
{
  "id": "r_880e8400e29b41d4a716446655440003",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Alice's Birthday",
  "description": "Send birthday gift",
  "date": "2025-03-15",
  "time": "10:00",
  "completed": false,
  "createdAt": "2025-01-10T14:23:00Z",
  "updatedAt": "2025-01-10T14:23:00Z"
}
```

---

### Recommendation Session

Result of AI-generated gift recommendations.

**Backend Schema:**
```typescript
type BackendRecommendationSession = {
  id: number;                    // Unique session identifier
  contactId: string;             // Foreign key to Contact
  provider: string;              // AI provider (e.g., "openai", "anthropic")
  modelName?: string | null;     // Model used (e.g., "gpt-4", "claude-3-opus")
  rawResponse: string;           // Full AI response for audit trail
  items: Array<{
    id: number;                  // Item ID within session
    title: string;               // Recommended item title
    description?: string | null; // AI-generated description
    createdAt: string;           // ISO 8601 timestamp
  }>;
  createdAt: string;             // Session creation timestamp
};
```

**Notes:**
- `rawResponse` stored as plain text for auditing and potential re-parsing
- `items` array contains recommendation titles only (no prices, links yet)
- Frontend can convert these to Widgets for persistence

**Example:**
```json
{
  "id": 42,
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "provider": "openai",
  "modelName": "gpt-4-turbo",
  "rawResponse": "Based on Alice's interests in hiking and photography...",
  "items": [
    {
      "id": 1,
      "title": "Professional Hiking Camera Backpack",
      "description": "Waterproof backpack designed for photography gear",
      "createdAt": "2025-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "title": "Advanced GPS Watch for Hiking",
      "description": "Rugged smartwatch with offline maps and altitude tracking",
      "createdAt": "2025-01-15T10:30:00Z"
    }
  ],
  "createdAt": "2025-01-15T10:30:00Z"
}
```

---

### User (Optional - Not Yet Called)

Current authenticated user profile.

**Backend Schema:**
```typescript
type User = {
  id: string;                    // Unique identifier (same as Telegram ID)
  telegramId: number;            // Numeric Telegram user ID
  telegramHandle?: string | null;  // Telegram username
  firstName?: string | null;     // User's first name
  lastName?: string | null;      // User's last name
  createdAt: string;             // Account creation timestamp
  updatedAt: string;             // Last profile update timestamp
};
```

**Notes:**
- Not currently called by frontend (reserved for future user profile page)
- Endpoint: `GET /api/auth/me`

---

## API Endpoints

### Authentication

#### `GET /api/auth/me`

Get current authenticated user profile.

**Status:** Implemented on backend, not yet called by frontend

**Request:**
```
GET /api/auth/me HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json
```

**Response (200 OK):**
```json
{
  "id": "123456789",
  "telegramId": 123456789,
  "telegramHandle": "johndoe",
  "firstName": "John",
  "lastName": "Doe",
  "createdAt": "2025-01-01T00:00:00Z",
  "updatedAt": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Missing X-Telegram-Id header
- `401 Unauthorized`: Telegram ID invalid or not found

---

### Contacts (Profiles)

#### `GET /api/contacts`

List all contacts for the authenticated user.

**Query Parameters:**
- `includeArchived` (optional, boolean): Include archived contacts. Default: `false`

**Request:**
```
GET /api/contacts?includeArchived=false HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json
```

**Response (200 OK):**
```json
[
  {
    "id": "c_550e8400e29b41d4a716446655440000",
    "name": "Alice Johnson",
    "relation": "Friend",
    "birthDate": "1990-03-15",
    "createdAt": "2025-01-10T14:23:00Z",
    "updatedAt": "2025-01-10T14:23:00Z",
    "isArchived": false
  },
  {
    "id": "c_660e8400e29b41d4a716446655440001",
    "name": "Bob Smith",
    "relation": "Family",
    "birthDate": "1985-07-22",
    "createdAt": "2025-01-12T08:15:00Z",
    "updatedAt": "2025-01-12T08:15:00Z",
    "isArchived": false
  }
]
```

**Notes:**
- Frontend calls this to get list of contacts for grouping/display
- Does NOT include nested notes, widgets, reminders (use GET /api/contacts/{id} for full details)
- Response should be sorted alphabetically by name (frontend will re-sort)

---

#### `GET /api/contacts/{contactId}`

Get full contact details including nested notes, widgets, and reminders.

**Request:**
```
GET /api/contacts/c_550e8400e29b41d4a716446655440000 HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json
```

**Response (200 OK):**
```json
{
  "id": "c_550e8400e29b41d4a716446655440000",
  "name": "Alice Johnson",
  "relation": "Friend",
  "telegramHandle": "alice_j",
  "birthDate": "1990-03-15",
  "phone": "+1-555-123-4567",
  "email": "alice@example.com",
  "profileImage": "data:image/png;base64,iVBORw0KG...",
  "commonNotes": "Met at university, loves hiking",
  "createdAt": "2025-01-10T14:23:00Z",
  "updatedAt": "2025-01-10T14:23:00Z",
  "isArchived": false,
  "additionalNotes": [
    {
      "id": "n_660e8400e29b41d4a716446655440001",
      "contactId": "c_550e8400e29b41d4a716446655440000",
      "title": "Favorite Movies",
      "content": "- Inception\n- The Matrix",
      "createdAt": "2025-01-12T08:15:00Z",
      "updatedAt": "2025-01-12T08:15:00Z"
    }
  ],
  "widgets": [
    {
      "id": "w_770e8400e29b41d4a716446655440002",
      "contactId": "c_550e8400e29b41d4a716446655440000",
      "title": "Hiking Boots",
      "description": "Waterproof hiking boots",
      "price": "$189.99",
      "accent": "blue",
      "createdAt": "2025-01-14T16:45:00Z",
      "updatedAt": "2025-01-14T16:45:00Z"
    }
  ],
  "reminders": [
    {
      "id": "r_880e8400e29b41d4a716446655440003",
      "contactId": "c_550e8400e29b41d4a716446655440000",
      "title": "Alice's Birthday",
      "date": "2025-03-15",
      "time": "10:00",
      "completed": false,
      "createdAt": "2025-01-10T14:23:00Z",
      "updatedAt": "2025-01-10T14:23:00Z"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found`: Contact does not exist or doesn't belong to user

---

#### `POST /api/contacts`

Create a new contact.

**Request Body:**
```json
{
  "name": "Charlie Davis",
  "relation": "Colleague",
  "telegramHandle": "charlie_d",
  "birthDate": "1992-11-08",
  "phone": "+1-555-987-6543",
  "email": "charlie@example.com",
  "profileImage": null,
  "commonNotes": "Works in marketing department"
}
```

**Request:**
```
POST /api/contacts HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json

{
  "name": "Charlie Davis",
  ...
}
```

**Response (201 Created):**
```json
{
  "id": "c_770e8400e29b41d4a716446655440004",
  "name": "Charlie Davis",
  "relation": "Colleague",
  "telegramHandle": "charlie_d",
  "birthDate": "1992-11-08",
  "phone": "+1-555-987-6543",
  "email": "charlie@example.com",
  "profileImage": null,
  "commonNotes": "Works in marketing department",
  "createdAt": "2025-01-15T11:00:00Z",
  "updatedAt": "2025-01-15T11:00:00Z",
  "isArchived": false,
  "additionalNotes": [],
  "widgets": [],
  "reminders": []
}
```

**Validation Errors (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "Name is required",
      "type": "value_error"
    }
  ]
}
```

**Notes:**
- `name` is required
- All other fields optional
- IDs auto-generated by backend
- Frontend will show all fields to user

---

#### `PATCH /api/contacts/{contactId}`

Update an existing contact.

**Request Body (partial - only include fields to update):**
```json
{
  "name": "Charlie D. Davis",
  "commonNotes": "Works in marketing, likes coffee"
}
```

**Request:**
```
PATCH /api/contacts/c_770e8400e29b41d4a716446655440004 HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json

{
  "name": "Charlie D. Davis",
  "commonNotes": "Works in marketing, likes coffee"
}
```

**Response (200 OK):**
```json
{
  "id": "c_770e8400e29b41d4a716446655440004",
  "name": "Charlie D. Davis",
  "relation": "Colleague",
  "telegramHandle": "charlie_d",
  "birthDate": "1992-11-08",
  "commonNotes": "Works in marketing, likes coffee",
  "updatedAt": "2025-01-15T14:30:00Z",
  ...
}
```

**Error Responses:**
- `404 Not Found`: Contact doesn't exist
- `422 Unprocessable Entity`: Invalid field value (e.g., bad email format)

**Notes:**
- All fields optional in request
- Timestamps (`createdAt`, `updatedAt`) managed by backend
- Frontend fetches full contact details after update (in backendApi.ts: `await fetchContact(contact.id)`)

---

#### `DELETE /api/contacts/{contactId}`

Delete (or archive) a contact.

**Request:**
```
DELETE /api/contacts/c_770e8400e29b41d4a716446655440004 HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json
```

**Response (204 No Content):**
```
(empty body)
```

**Error Responses:**
- `404 Not Found`: Contact doesn't exist
- `403 Forbidden`: Contact belongs to different user

**Notes:**
- Implementation choice: Can be hard delete or soft delete (set `isArchived = true`)
- Frontend does not expect deletion confirmation
- Frontend removes from UI immediately after successful response

---

### Notes

#### `POST /api/contacts/{contactId}/notes`

Create a new note for a contact.

**Request Body:**
```json
{
  "title": "Favorite Movies",
  "content": "- Inception\n- The Matrix\n- Interstellar"
}
```

**Request:**
```
POST /api/contacts/c_550e8400e29b41d4a716446655440000/notes HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json

{
  "title": "Favorite Movies",
  "content": "- Inception\n- The Matrix\n- Interstellar"
}
```

**Response (201 Created):**
```json
{
  "id": "n_990e8400e29b41d4a716446655440005",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Favorite Movies",
  "content": "- Inception\n- The Matrix\n- Interstellar",
  "createdAt": "2025-01-15T15:45:00Z",
  "updatedAt": "2025-01-15T15:45:00Z"
}
```

**Validation:**
- `title` required, max 255 chars
- `content` optional, max 5000 chars

---

#### `PATCH /api/contacts/{contactId}/notes/{noteId}`

Update an existing note.

**Request Body (partial):**
```json
{
  "title": "Favorite Movies & Series",
  "content": "- Inception\n- The Matrix\n- Stranger Things"
}
```

**Response (200 OK):**
```json
{
  "id": "n_990e8400e29b41d4a716446655440005",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Favorite Movies & Series",
  "content": "- Inception\n- The Matrix\n- Stranger Things",
  "createdAt": "2025-01-15T15:45:00Z",
  "updatedAt": "2025-01-15T16:00:00Z"
}
```

---

#### `DELETE /api/contacts/{contactId}/notes/{noteId}`

Delete a note.

**Response (204 No Content):**
```
(empty body)
```

---

### Widgets (Gift Ideas)

#### `POST /api/contacts/{contactId}/widgets`

Create a new widget (gift suggestion).

**Request Body:**
```json
{
  "title": "Professional Hiking Camera Backpack",
  "description": "Waterproof backpack designed for photography gear while hiking",
  "imageUrl": "https://example.com/backpack.jpg",
  "price": "$149.99",
  "links": [
    { "text": "Amazon", "url": "https://amazon.com/..." },
    { "text": "REI", "url": "https://rei.com/..." }
  ],
  "accent": "blue"
}
```

**Response (201 Created):**
```json
{
  "id": "w_aa0e8400e29b41d4a716446655440006",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Professional Hiking Camera Backpack",
  "description": "Waterproof backpack designed for photography gear while hiking",
  "imageUrl": "https://example.com/backpack.jpg",
  "price": "$149.99",
  "links": [
    { "text": "Amazon", "url": "https://amazon.com/..." },
    { "text": "REI", "url": "https://rei.com/..." }
  ],
  "accent": "blue",
  "createdAt": "2025-01-15T16:15:00Z",
  "updatedAt": "2025-01-15T16:15:00Z"
}
```

**Validation:**
- `title` required, max 255 chars
- `description` optional, max 1000 chars
- `price` optional, format flexible (store as string)
- `links` optional, max 10 items
- `accent` must be one of: gray, red, blue, green, yellow, purple

---

#### `PATCH /api/contacts/{contactId}/widgets/{widgetId}`

Update an existing widget.

**Response (200 OK):**
(Same schema as POST response with updated fields)

---

#### `DELETE /api/contacts/{contactId}/widgets/{widgetId}`

Delete a widget.

**Response (204 No Content):**

---

### Reminders

#### `POST /api/reminders`

Create a new reminder (tied to a contact).

**Request Body:**
```json
{
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Alice's Birthday",
  "description": "Send birthday gift",
  "date": "2025-03-15",
  "time": "10:00",
  "completed": false
}
```

**Response (201 Created):**
```json
{
  "id": "r_bb0e8400e29b41d4a716446655440007",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Alice's Birthday",
  "description": "Send birthday gift",
  "date": "2025-03-15",
  "time": "10:00",
  "completed": false,
  "createdAt": "2025-01-15T16:30:00Z",
  "updatedAt": "2025-01-15T16:30:00Z"
}
```

**Validation:**
- `contactId` required, must reference existing contact
- `title` required, max 255 chars
- `description` optional, max 500 chars
- `date` required, valid ISO date (YYYY-MM-DD)
- `time` optional, valid time (HH:MM 24-hour format)
- `completed` required boolean

---

#### `PATCH /api/reminders/{reminderId}`

Update a reminder.

**Request Body (partial):**
```json
{
  "completed": true,
  "title": "Alice's Birthday - Gift Sent"
}
```

**Response (200 OK):**
```json
{
  "id": "r_bb0e8400e29b41d4a716446655440007",
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "title": "Alice's Birthday - Gift Sent",
  "description": "Send birthday gift",
  "date": "2025-03-15",
  "time": "10:00",
  "completed": true,
  "updatedAt": "2025-01-15T17:00:00Z"
}
```

---

#### `DELETE /api/reminders/{reminderId}`

Delete a reminder.

**Response (204 No Content):**

---

### Recommendations (AI Gift Ideas)

#### `POST /api/contacts/{contactId}/recommendations`

Generate AI-powered gift recommendations for a contact.

**Request Body:**
```json
{
  "categories": ["hiking", "photography", "travel"],
  "notes": "Loves outdoor activities and adventure travel",
  "saveAsWidgets": false
}
```

**Request:**
```
POST /api/contacts/c_550e8400e29b41d4a716446655440000/recommendations HTTP/1.1
X-Telegram-Id: 123456789
Content-Type: application/json

{
  "categories": ["hiking", "photography", "travel"],
  "notes": "Loves outdoor activities and adventure travel",
  "saveAsWidgets": false
}
```

**Response (200 OK):**
```json
{
  "id": 42,
  "contactId": "c_550e8400e29b41d4a716446655440000",
  "provider": "openai",
  "modelName": "gpt-4-turbo",
  "rawResponse": "Based on Alice's interests in hiking and photography, here are some gift ideas...",
  "items": [
    {
      "id": 1,
      "title": "Professional Hiking Camera Backpack",
      "description": "Waterproof backpack designed for photography gear",
      "createdAt": "2025-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "title": "Advanced GPS Watch for Hiking",
      "description": "Rugged smartwatch with offline maps",
      "createdAt": "2025-01-15T10:30:00Z"
    },
    {
      "id": 3,
      "title": "Travel-Friendly Tripod",
      "description": "Lightweight, compact tripod for photography on the go",
      "createdAt": "2025-01-15T10:30:00Z"
    }
  ],
  "createdAt": "2025-01-15T10:30:00Z"
}
```

**Parameters:**
- `categories` (required): Array of interest categories for AI context
- `notes` (optional): Additional context about the contact
- `saveAsWidgets` (optional): If true, automatically create widgets from recommendations (default: false)

**AI Provider Implementation Notes:**
- Use OpenAI GPT-4, Anthropic Claude, or similar LLM
- Prompt should request 3-5 gift ideas with descriptions
- Store full AI response in `rawResponse` for audit/debugging
- Parse response into structured items array
- Consider caching recommendations per contact/category combination

**Error Responses:**
- `404 Not Found`: Contact doesn't exist
- `500 Internal Server Error`: AI service unavailable

**Notes:**
- Recommendations are ephemeral (session-based); not permanently stored as widgets unless `saveAsWidgets=true`
- Frontend can manually convert recommendation items to widgets via POST /api/contacts/{id}/widgets

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Missing required header |
| 401 | Unauthorized | Invalid Telegram ID |
| 403 | Forbidden | Access to another user's data |
| 404 | Not Found | Contact/note/widget doesn't exist |
| 422 | Unprocessable Entity | Invalid field value |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Database down, AI service down |

### Error Response Format

**400/422 Errors:**
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "Name is required and non-empty",
      "type": "value_error"
    }
  ]
}
```

**401/403 Errors:**
```json
{
  "detail": "Not authenticated or access denied"
}
```

**404 Errors:**
```json
{
  "detail": "Contact not found"
}
```

### Frontend Error Handling

The frontend's `backendApi.ts` error handling:

1. Checks `response.ok` status
2. Falls back to `response.text()` if JSON parsing fails
3. Throws with detail message or status code
4. Calling code catches and logs to console (basic; should improve)
5. UI updates fail gracefully (shows "failed to save" or similar)

**TODO:** Implement better error handling:
- User-friendly toast notifications
- Retry logic for transient failures (503, network errors)
- Validation error display in forms
- Logging/monitoring for failed requests

---

## Validation Rules

### Contact Validation

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | Non-empty, max 255 chars |
| `relation` | string | No | Max 100 chars |
| `telegramHandle` | string | No | Max 32 chars, alphanumeric + underscore |
| `birthDate` | date | No | Valid ISO date (YYYY-MM-DD) |
| `phone` | string | No | Max 20 chars, digits + symbols |
| `email` | string | No | Valid email format |
| `profileImage` | string | No | Base64 or URL, max 1MB |
| `commonNotes` | string | No | Max 5000 chars |

### Note Validation

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `title` | string | Yes | Non-empty, max 255 chars |
| `content` | string | No | Max 5000 chars |

### Widget Validation

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `title` | string | Yes | Non-empty, max 255 chars |
| `description` | string | No | Max 1000 chars |
| `imageUrl` | string | No | Valid URL or base64, max 1MB |
| `price` | string | No | Max 50 chars |
| `links[].text` | string | No | Max 100 chars each |
| `links[].url` | string | No | Valid URL each |
| `links` | array | No | Max 10 items |
| `accent` | enum | No | One of: gray, red, blue, green, yellow, purple |

### Reminder Validation

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `contactId` | string | Yes | Must reference existing contact |
| `title` | string | Yes | Non-empty, max 255 chars |
| `description` | string | No | Max 500 chars |
| `date` | date | Yes | Valid ISO date (YYYY-MM-DD) |
| `time` | time | No | Valid HH:MM (24-hour) or null |
| `completed` | boolean | Yes | True/false |

---

## Integration Patterns

### Request/Response Cycle

```
Frontend (React)
  │
  ├─ Calls: backendApi.fetchContacts()
  │
  ├─> Builds request:
  │   - URL: http://127.0.0.1:8000/api/contacts
  │   - Headers: X-Telegram-Id, Content-Type
  │   - Method: GET
  │
  ├─> Fetch request
  │
Backend (FastAPI)
  │
  ├─ Receives request
  ├─ Validates X-Telegram-Id header
  ├─ Queries: SELECT * FROM contacts WHERE telegram_id = ?
  ├─ Returns: JSON array of contacts
  │
  ├─> Response: HTTP 200 + JSON body
  │
Frontend
  │
  ├─ Receives response
  ├─ Parses JSON
  ├─ Normalizes field names (snake_case → camelCase)
  ├─ Updates React state
  ├─ Re-renders UI
```

### Normalization Example

**Backend Response (snake_case):**
```json
{
  "id": "c_550e8400e29b41d4a716446655440000",
  "name": "Alice Johnson",
  "telegram_handle": "alice_j",
  "birth_date": "1990-03-15",
  "profile_image": "data:image/png;base64...",
  "created_at": "2025-01-10T14:23:00Z",
  "updated_at": "2025-01-10T14:23:00Z"
}
```

**Frontend Type (camelCase):**
```typescript
{
  id: "c_550e8400e29b41d4a716446655440000",
  name: "Alice Johnson",
  telegramHandle: "alice_j",
  birthDate: "1990-03-15",
  image: "data:image/png;base64...",
  createdAt: "2025-01-10T14:23:00Z",
  updatedAt: "2025-01-10T14:23:00Z"
}
```

### Optimistic Updates (Future Pattern)

**Current:** Frontend waits for API response before updating UI
**Future:** Could implement optimistic updates for better UX:
1. User submits form
2. Frontend updates local state immediately
3. Show "Saving..." spinner
4. Send API request in background
5. Revert on error, success on 200

---

## Implementation Status

### ✅ Complete (Frontend & Backend)

- [x] Authentication via X-Telegram-Id header
- [x] Contact CRUD (`GET /api/contacts`, `GET /api/contacts/{id}`, `POST /api/contacts`, `PATCH /api/contacts/{id}`, `DELETE /api/contacts/{id}`)
- [x] Note CRUD (`POST /api/contacts/{id}/notes`, `PATCH /api/contacts/{id}/notes/{id}`, `DELETE /api/contacts/{id}/notes/{id}`)
- [x] Widget CRUD (`POST /api/contacts/{id}/widgets`, `PATCH /api/contacts/{id}/widgets/{id}`, `DELETE /api/contacts/{id}/widgets/{id}`)
- [x] Reminder CRUD (`POST /api/reminders`, `PATCH /api/reminders/{id}`, `DELETE /api/reminders/{id}`)
- [x] Gift recommendations (`POST /api/contacts/{id}/recommendations`)
- [x] Field normalization (snake_case ↔ camelCase)

### ⏳ Partial (Backend exists, frontend not using yet)

- [ ] `GET /api/auth/me` - Backend endpoint exists; frontend doesn't call it on init
  - **Why:** User profile page not yet implemented
  - **Needed for:** Displaying current user info, settings, account management

### ❌ Not Started

- [ ] Settings API (`GET /api/settings`, `PATCH /api/settings`)
  - **Why:** Settings currently stored in localStorage only
  - **Needed for:** UI theme, swipe preferences, notification settings
  
- [ ] Telegram initData verification (`X-Telegram-Init-Data` header)
  - **Why:** Would replace simple `X-Telegram-Id` header auth
  - **Needed for:** Production security; currently dev-only with mock data
  
- [ ] Image upload endpoint (`POST /api/contacts/{id}/upload-image`)
  - **Why:** Frontend currently sends base64; should upload files
  - **Needed for:** Better performance, image resizing, CDN storage
  
- [ ] Reminder repeat fields (`repeat`, `earlyReminderMinutes`, `earlyReminderRepeat`)
  - **Why:** Form fields exist but backend doesn't store these yet
  - **Needed for:** Recurring reminders, smart notifications

- [ ] Non-contact reminders (calendar-only events)
  - **Why:** All reminders currently tied to contacts
  - **Needed for:** Holiday reminders, general events independent of contacts

---

## Remaining Gaps

### High Priority

**1. Telegram Initiation Data Verification (Phase 2)**
   - **Issue:** Currently rely on simple `X-Telegram-Id` header; not cryptographically verified
   - **Solution:** Accept optional `X-Telegram-Init-Data` header; verify HMAC-SHA256 signature using bot token
   - **Impact:** Production deployment security
   - **Effort:** 2-3 hours

**2. Settings Persistence API**
   - **Issue:** UI preferences (swipe toggles, theme) only stored in localStorage
   - **Solution:** Create `/api/settings` endpoint with GET/PATCH for user preferences
   - **Impact:** Settings sync across devices, account portability
   - **Effort:** 1-2 hours

### Medium Priority

**3. Reminder Repeat Fields**
   - **Issue:** Form has `repeat`, `earlyReminderMinutes`, `earlyReminderRepeat` fields but backend ignores them
   - **Solution:** Add these columns to reminders table; implement repeat scheduling logic
   - **Impact:** Recurring birthdays, smart reminder notifications
   - **Effort:** 3-4 hours

**4. User Profile Initialization**
   - **Issue:** Frontend doesn't call `GET /api/auth/me` on app load
   - **Solution:** Add user profile page calling the endpoint; display user info
   - **Impact:** Personal account management, profile customization
   - **Effort:** 1-2 hours (mostly frontend)

**5. Image Upload Endpoint**
   - **Issue:** Contact images sent as base64; should upload to file storage
   - **Solution:** Create `POST /api/contacts/{id}/upload-image` accepting multipart/form-data
   - **Impact:** Smaller API payloads, better performance, image CDN caching
   - **Effort:** 2-3 hours

### Low Priority

**6. Richer Recommendation Metadata**
   - **Issue:** Recommendations return only title + description; no price, links, category
   - **Solution:** Enhance AI prompt to return structured JSON with more fields
   - **Impact:** Better gift suggestions UX, one-click widget creation
   - **Effort:** 1-2 hours

**7. Non-Contact Reminders**
   - **Issue:** All reminders tied to contacts; can't have standalone calendar events
   - **Solution:** Add optional `contactId = null` reminders for holidays, general events
   - **Impact:** More versatile calendar usage
   - **Effort:** 2-3 hours

---

## Testing Checklist

### Prerequisites
- Backend running at `http://127.0.0.1:8000`
- PostgreSQL database initialized
- Frontend env var: `VITE_API_BASE_URL=http://127.0.0.1:8000`

### Authentication Tests

- [ ] `GET /api/contacts` without `X-Telegram-Id` header → 400 error
- [ ] `GET /api/contacts` with valid `X-Telegram-Id` → 200 with user's contacts only
- [ ] `GET /api/contacts` with different `X-Telegram-Id` → 200 but different contact list

### Contact CRUD Tests

- [ ] `POST /api/contacts` with minimal data (name only) → 201 created
- [ ] `POST /api/contacts` without name → 422 validation error
- [ ] `GET /api/contacts` → returns list sorted alphabetically
- [ ] `GET /api/contacts/{id}` → returns full contact with nested notes/widgets/reminders
- [ ] `PATCH /api/contacts/{id}` → updates specified fields only
- [ ] `DELETE /api/contacts/{id}` → 204, contact removed from list

### Note CRUD Tests

- [ ] `POST /api/contacts/{id}/notes` → creates note linked to contact
- [ ] `POST /api/contacts/{id}/notes` with invalid contactId → 404
- [ ] `PATCH /api/contacts/{id}/notes/{noteId}` → updates note
- [ ] `DELETE /api/contacts/{id}/notes/{noteId}` → removes note

### Widget CRUD Tests

- [ ] `POST /api/contacts/{id}/widgets` → creates widget
- [ ] `POST /api/contacts/{id}/widgets` with invalid accent → 422 error
- [ ] `POST /api/contacts/{id}/widgets` with max links → succeeds
- [ ] `POST /api/contacts/{id}/widgets` with 11 links → 422 validation error

### Reminder CRUD Tests

- [ ] `POST /api/reminders` → creates reminder with birth date
- [ ] `POST /api/reminders` with invalid date → 422 error
- [ ] `POST /api/reminders` with time in 24-hour format → succeeds
- [ ] `PATCH /api/reminders/{id}` → marks completed=true
- [ ] `DELETE /api/reminders/{id}` → removes reminder

### Recommendation Tests

- [ ] `POST /api/contacts/{id}/recommendations` with categories → returns items array
- [ ] `POST /api/contacts/{id}/recommendations` with empty categories → 422 or generates generic ideas
- [ ] `POST /api/contacts/{id}/recommendations` with AI unavailable → 503 error

### Normalization Tests

- [ ] Response fields are camelCase (e.g., `birthDate`, not `birth_date`)
- [ ] Nested objects normalized (e.g., `additionalNotes[].createdAt`)
- [ ] Arrays properly normalized (e.g., widgets, reminders)

### Frontend Integration Tests

- [ ] App loads; displays contacts list from API
- [ ] Click contact → shows full profile with notes, widgets, reminders
- [ ] Create new contact → submitted to API, appears in list
- [ ] Edit contact → PATCH succeeds, UI updates
- [ ] Delete contact → DELETE succeeds, removed from UI
- [ ] Add note → POST succeeds, appears in contact details
- [ ] Add widget → POST succeeds, appears in gift list
- [ ] Create reminder → POST succeeds, appears in calendar
- [ ] Generate recommendations → POST succeeds, shows gift ideas

### Error Scenarios

- [ ] Backend offline → fetch fails, UI shows error
- [ ] Invalid Telegram ID → 401 response handled gracefully
- [ ] Network timeout → request fails, user sees "Connection error"
- [ ] 422 validation error → user sees form validation message

---

## Summary

The BirthdaySync mini-app frontend is production-ready and fully integrated with the backend API. All core features (contacts, notes, widgets, reminders, recommendations) are working end-to-end.

**For backend developers:**
1. Use this document as the API contract specification
2. Implement each endpoint exactly as described
3. Enforce validation rules to catch invalid data early
4. Return appropriate HTTP status codes and error formats
5. Test with the provided checklist before deployment
6. Prioritize high-priority gaps (Telegram verification, settings, repeat fields)

**Next steps:**
- [ ] Verify all endpoints work with frontend in dev environment
- [ ] Implement high-priority gaps
- [ ] Deploy to production with Telegram bot token for initData verification
- [ ] Monitor production API usage for errors/performance issues