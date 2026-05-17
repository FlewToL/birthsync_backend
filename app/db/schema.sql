CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    birth_date DATE,
    phone TEXT,
    email TEXT,
    profile_image TEXT,
    common_notes TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'ru',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS common_notes TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_language TEXT NOT NULL DEFAULT 'ru';

CREATE TABLE IF NOT EXISTS user_cards (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name TEXT,
    birth_date DATE,
    about TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contacts (
    id BIGSERIAL PRIMARY KEY,
    public_id UUID NOT NULL DEFAULT gen_random_uuid(),
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    relation TEXT,
    telegram_handle TEXT,
    birth_date DATE,
    phone TEXT,
    email TEXT,
    profile_image TEXT,
    common_notes TEXT,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT contacts_status_check CHECK (status IN ('pending', 'confirmed', 'declined'))
);

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS public_id UUID;
UPDATE contacts SET public_id = gen_random_uuid() WHERE public_id IS NULL;
ALTER TABLE contacts ALTER COLUMN public_id SET DEFAULT gen_random_uuid();
ALTER TABLE contacts ALTER COLUMN public_id SET NOT NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS profile_image TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS common_notes TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS telegram_handle TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_public_id ON contacts(public_id);
CREATE INDEX IF NOT EXISTS idx_contacts_owner_user_id ON contacts(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_contacts_contact_user_id ON contacts(contact_user_id);

CREATE TABLE IF NOT EXISTS user_categories (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    theme TEXT NOT NULL DEFAULT 'system',
    swipe_enabled BOOLEAN NOT NULL DEFAULT true,
    notifications_enabled BOOLEAN NOT NULL DEFAULT true,
    birthday_reminder_days INTEGER NOT NULL DEFAULT 1,
    gift_recommendations_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_settings_theme_check CHECK (theme IN ('system', 'light', 'dark')),
    CONSTRAINT user_settings_birthday_reminder_days_check CHECK (
        birthday_reminder_days >= 0 AND birthday_reminder_days <= 365
    )
);

ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS theme TEXT NOT NULL DEFAULT 'system';
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS swipe_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS birthday_reminder_days INTEGER NOT NULL DEFAULT 1;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS gift_recommendations_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS wishlists (
    id BIGSERIAL PRIMARY KEY,
    owner_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wishlists_owner_user_id ON wishlists(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_wishlists_contact_id ON wishlists(contact_id);

CREATE TABLE IF NOT EXISTS wishlist_items (
    id BIGSERIAL PRIMARY KEY,
    wishlist_id BIGINT NOT NULL REFERENCES wishlists(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT wishlist_items_status_check CHECK (status IN ('active', 'reserved', 'bought', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_wishlist_items_wishlist_id ON wishlist_items(wishlist_id);

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    event_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_event_date ON events(event_date);

CREATE TABLE IF NOT EXISTS recommendation_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wishlist_id BIGINT REFERENCES wishlists(id) ON DELETE SET NULL,
    contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    model_name TEXT,
    prompt_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_response TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL;
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS raw_response TEXT;
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed';
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS error_message TEXT;

CREATE INDEX IF NOT EXISTS idx_recommendation_sessions_user_id ON recommendation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_sessions_contact_id ON recommendation_sessions(contact_id);

CREATE TABLE IF NOT EXISTS recommendation_items (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES recommendation_sessions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    score NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reminder_jobs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id BIGINT REFERENCES events(id) ON DELETE CASCADE,
    remind_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT reminder_jobs_status_check CHECK (status IN ('scheduled', 'sent', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_reminder_jobs_remind_at ON reminder_jobs(remind_at);
CREATE INDEX IF NOT EXISTS idx_reminder_jobs_user_id ON reminder_jobs(user_id);

CREATE TABLE IF NOT EXISTS reminder_logs (
    id BIGSERIAL PRIMARY KEY,
    reminder_job_id BIGINT NOT NULL REFERENCES reminder_jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contact_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contact_notes_contact_id ON contact_notes(contact_id);

CREATE TABLE IF NOT EXISTS contact_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    price TEXT,
    links JSONB NOT NULL DEFAULT '[]'::jsonb,
    accent TEXT NOT NULL DEFAULT 'gray',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT contact_widgets_accent_check CHECK (
        accent IN ('gray', 'red', 'blue', 'green', 'yellow', 'purple')
    )
);

ALTER TABLE contact_widgets DROP CONSTRAINT IF EXISTS contact_widgets_accent_check;
UPDATE contact_widgets
SET accent = 'gray'
WHERE accent IS NULL OR accent NOT IN ('gray', 'red', 'blue', 'green', 'yellow', 'purple');
ALTER TABLE contact_widgets ALTER COLUMN accent SET DEFAULT 'gray';
ALTER TABLE contact_widgets
    ADD CONSTRAINT contact_widgets_accent_check CHECK (
        accent IN ('gray', 'red', 'blue', 'green', 'yellow', 'purple')
    );

CREATE INDEX IF NOT EXISTS idx_contact_widgets_contact_id ON contact_widgets(contact_id);

CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    reminder_date DATE NOT NULL,
    reminder_time TIME,
    completed BOOLEAN NOT NULL DEFAULT false,
    repeat_rule TEXT,
    early_reminder_minutes INTEGER,
    early_reminder_repeat TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT reminders_repeat_rule_check CHECK (
        repeat_rule IS NULL OR repeat_rule IN ('daily', 'weekly', 'monthly', 'yearly')
    ),
    CONSTRAINT reminders_early_reminder_minutes_check CHECK (
        early_reminder_minutes IS NULL OR early_reminder_minutes BETWEEN 0 AND 525600
    ),
    CONSTRAINT reminders_early_reminder_repeat_check CHECK (
        early_reminder_repeat IS NULL OR early_reminder_repeat IN ('once', 'daily')
    )
);

ALTER TABLE reminders ADD COLUMN IF NOT EXISTS repeat_rule TEXT;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS early_reminder_minutes INTEGER;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS early_reminder_repeat TEXT;
ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_repeat_rule_check;
ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_early_reminder_minutes_check;
ALTER TABLE reminders DROP CONSTRAINT IF EXISTS reminders_early_reminder_repeat_check;
ALTER TABLE reminders
    ADD CONSTRAINT reminders_repeat_rule_check CHECK (
        repeat_rule IS NULL OR repeat_rule IN ('daily', 'weekly', 'monthly', 'yearly')
    );
ALTER TABLE reminders
    ADD CONSTRAINT reminders_early_reminder_minutes_check CHECK (
        early_reminder_minutes IS NULL OR early_reminder_minutes BETWEEN 0 AND 525600
    );
ALTER TABLE reminders
    ADD CONSTRAINT reminders_early_reminder_repeat_check CHECK (
        early_reminder_repeat IS NULL OR early_reminder_repeat IN ('once', 'daily')
    );

CREATE INDEX IF NOT EXISTS idx_reminders_contact_id ON reminders(contact_id);
CREATE INDEX IF NOT EXISTS idx_reminders_date ON reminders(reminder_date);

CREATE TABLE IF NOT EXISTS reminder_notifications (
    id BIGSERIAL PRIMARY KEY,
    reminder_id UUID NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    notification_key TEXT NOT NULL,
    occurrence_at TIMESTAMPTZ NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT reminder_notifications_type_check CHECK (
        notification_type IN ('main', 'early')
    ),
    CONSTRAINT reminder_notifications_status_check CHECK (
        status IN ('processing', 'sent', 'failed')
    ),
    UNIQUE (reminder_id, notification_key)
);

CREATE INDEX IF NOT EXISTS idx_reminder_notifications_user_id ON reminder_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_reminder_notifications_scheduled_at ON reminder_notifications(scheduled_at);
