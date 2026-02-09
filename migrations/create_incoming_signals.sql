-- Incoming Signals table for tracking unread messages + typing indicators
-- Used by the operator dashboard to show WhatsApp-style unread badges

CREATE TABLE IF NOT EXISTS incoming_signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'messenger',
    display_name TEXT DEFAULT '',
    message_preview TEXT DEFAULT '',
    unread_count INTEGER NOT NULL DEFAULT 0,
    is_typing BOOLEAN NOT NULL DEFAULT false,
    last_message_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(company_id, user_id)
);

-- Index for fast lookup by company
CREATE INDEX IF NOT EXISTS idx_incoming_signals_company
    ON incoming_signals(company_id);

-- Index for unread queries
CREATE INDEX IF NOT EXISTS idx_incoming_signals_unread
    ON incoming_signals(company_id, unread_count) WHERE unread_count > 0;

-- RLS policies
ALTER TABLE incoming_signals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on incoming_signals"
    ON incoming_signals
    FOR ALL
    USING (true)
    WITH CHECK (true);
