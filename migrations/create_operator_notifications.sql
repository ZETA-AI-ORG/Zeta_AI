-- ══════════════════════════════════════════════════════════════
-- Table: operator_notifications
-- Purpose: Store messages from clients whose bot is OFF (post-order)
--          so the human operator can see and respond via the PWA.
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS operator_notifications (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    message     TEXT NOT NULL DEFAULT '',
    message_type TEXT NOT NULL DEFAULT 'post_order',
    order_summary JSONB DEFAULT '{}'::jsonb,
    read        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast polling by company (unread first)
CREATE INDEX IF NOT EXISTS idx_opnotif_company_read
    ON operator_notifications (company_id, read, created_at DESC);

-- Index for marking all read for a specific user
CREATE INDEX IF NOT EXISTS idx_opnotif_company_user
    ON operator_notifications (company_id, user_id);

-- RLS: enable row-level security
ALTER TABLE operator_notifications ENABLE ROW LEVEL SECURITY;

-- Policy: service role can do everything (backend uses service key)
CREATE POLICY "service_role_all" ON operator_notifications
    FOR ALL
    USING (true)
    WITH CHECK (true);
