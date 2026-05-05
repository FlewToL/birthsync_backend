import { Note } from "@/types/note";
import { Reminder } from "@/types/reminder";
import { Widget } from "@/types/widget";

/**
 * Profile type - client-side representation combining Contact with related data
 * 
 * Note: This is a composite view of a Contact along with its associated Notes, Widgets, and Reminders.
 * In a backend-integrated system:
 * - Contact data comes from GET /api/contacts/:id
 * - Additional Notes come from GET /api/contacts/:id/notes
 * - Widgets come from GET /api/contacts/:id/widgets
 * - Reminders come from GET /api/reminders?contactId=:id
 * 
 * For now, this remains a local client-side type that mirrors the Contact schema.
 */
export interface Profile {
  id: string; // UUID (Contact ID)
  name: string; // Contact name
  relation?: string; // Optional: relationship
  telegramHandle?: string; // Optional: Telegram handle (if contact is a Telegram user)
  birthDate?: string; // ISO 8601 date (YYYY-MM-DD)
  phone?: string; // Optional: phone number
  email?: string; // Optional: email
  image?: string; // Optional: base64 profile image (client-side storage)
  commonNotes: string; // Shared bio/notes
  additionalNotes: Note[]; // Array of Note objects
  widgets: Widget[]; // Array of gift/present ideas
  reminders: Reminder[]; // Array of birthday reminders
  createdAt?: string; // ISO 8601 timestamp (when contact was added)
  updatedAt?: string; // ISO 8601 timestamp (last profile update)
}

export type ProfileView = 'notes' | 'presents';
export type ProfileMode = 'view' | 'edit';
