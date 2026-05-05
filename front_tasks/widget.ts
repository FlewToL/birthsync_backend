/**
 * WidgetLink type for backend integration
 * Represents a link entry for a widget (gift idea) with both text and URL
 */
export interface WidgetLink {
  text: string; // Display text (e.g., "Shop Name", "Buy on Amazon")
  url: string; // Full URL (e.g., "https://amazon.com/...")
}

/**
 * Widget type for backend integration
 * Represents a gift idea/present for a contact
 * Backend endpoint: POST /api/contacts/:contactId/widgets, GET /api/contacts/:contactId/widgets
 */
export interface Widget {
  id: string; // UUID
  contactId: string; // Foreign key: Contact.id (which contact this gift is for)
  title: string; // Gift name (e.g., "Concert Ticket")
  description?: string; // Optional: detailed description
  imageUrl?: string; // Optional: base64 or image URL for gift picture
  price?: string; // Optional: price (e.g., "₽ 5000")
  links?: WidgetLink[]; // Optional: array of {text, url} for purchase links
  accent?: 'gray' | 'blue' | 'photo'; // Display style variant
  createdAt: string; // ISO 8601 timestamp
  updatedAt: string; // ISO 8601 timestamp
}

/**
 * Backend schema mapping for Widget API:
 * 
 * POST /api/contacts/:contactId/widgets
 * Request: { title, description?, imageUrl?, price?, links?, accent? }
 * Response: Widget (full object with id, contactId, createdAt, updatedAt)
 * 
 * GET /api/contacts/:contactId/widgets
 * Response: Widget[]
 * 
 * PATCH /api/contacts/:contactId/widgets/:id
 * Request: Partial<Widget> (any updatable field except id, contactId, createdAt)
 * Response: Widget
 * 
 * DELETE /api/contacts/:contactId/widgets/:id
 * Response: { success: boolean }
 */