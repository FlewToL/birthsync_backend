/**
 * Note type for backend integration
 * Represents an additional note about a contact
 * Backend endpoint: POST /api/contacts/:contactId/notes, GET /api/contacts/:contactId/notes
 */
export interface Note {
  id: string; // UUID
  contactId: string; // Foreign key: Contact.id (which contact this note belongs to)
  title: string; // Note title
  content: string; // Note content/body
  createdAt: string; // ISO 8601 timestamp
  updatedAt: string; // ISO 8601 timestamp
}

/**
 * Backend schema mapping for Note API:
 * 
 * POST /api/contacts/:contactId/notes
 * Request: { title, content }
 * Response: Note (full object with id, contactId, createdAt, updatedAt)
 * 
 * GET /api/contacts/:contactId/notes
 * Response: Note[]
 * 
 * PATCH /api/contacts/:contactId/notes/:id
 * Request: Partial<Note> (any updatable field except id, contactId, createdAt)
 * Response: Note
 * 
 * DELETE /api/contacts/:contactId/notes/:id
 * Response: { success: boolean }
 */