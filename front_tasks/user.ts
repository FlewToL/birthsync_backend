/**
 * User type for backend integration
 * Represents the authenticated user's profile (Telegram user)
 * Backend endpoint: GET /api/auth/me, PATCH /api/auth/profile
 */
export interface User {
  id: string; // Telegram user ID
  telegramId: number; // Numeric Telegram ID
  telegramHandle?: string; // Telegram username (without @)
  firstName: string; // First name from Telegram
  lastName?: string; // Last name from Telegram
  birthDate?: string; // ISO 8601 date format (YYYY-MM-DD) - user can set their own
  phone?: string; // Optional: phone number for settings
  email?: string; // Optional: email for notifications
  profileImage?: string; // Optional: base64 or image URL for user profile picture
  commonNotes?: string; // Optional: bio/about section
  preferredLanguage?: string; // Default: 'ru' | 'en'
  createdAt: string; // ISO 8601 timestamp (account creation)
  updatedAt: string; // ISO 8601 timestamp (last profile update)
}

/**
 * Backend schema mapping for User API:
 * 
 * GET /api/auth/me
 * Response: User (authenticated user's profile)
 * 
 * PATCH /api/auth/profile
 * Request: Partial<User> (excludes telegramId, createdAt)
 * Response: User
 * 
 * Note: Telegram ID and handle come from Telegram SDK and cannot be changed
 */
