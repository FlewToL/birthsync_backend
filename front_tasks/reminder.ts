/**
 * Reminder type for backend integration
 * Represents a birthday reminder for a contact
 * Backend endpoint: POST /api/reminders, GET /api/reminders, PATCH /api/reminders/:id
 */
export interface Reminder {
  id: string; // UUID
  contactId: string; // Foreign key: Contact.id
  title: string; // Reminder title (e.g., "Birthday reminder")
  description?: string; // Optional: additional details
  date: string; // ISO 8601 date (reminder date, typically same as birthDate)
  time?: string; // Optional: time in HH:mm format
  completed: boolean; // Flag for whether reminder has been acted on
  createdAt: string; // ISO 8601 timestamp
  updatedAt: string; // ISO 8601 timestamp
}

/**
 * Backend schema mapping for Reminder API:
 * 
 * POST /api/reminders
 * Request: { contactId, title, description?, date, time?, completed? }
 * Response: Reminder (full object with id, createdAt, updatedAt)
 * 
 * GET /api/reminders
 * Query: ?contactId=:id | ?upcoming=true (for birthdays coming soon)
 * Response: Reminder[]
 * 
 * PATCH /api/reminders/:id
 * Request: Partial<Reminder> (any updatable field except id, contactId, createdAt)
 * Response: Reminder
 * 
 * DELETE /api/reminders/:id
 * Response: { success: boolean }
 */