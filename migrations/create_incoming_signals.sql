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

CREATE OR REPLACE FUNCTION incoming_signal_upsert(
    p_company_id text,
    p_user_id text,
    p_channel text DEFAULT 'messenger',
    p_display_name text DEFAULT '',
    p_message_preview text DEFAULT ''
)
RETURNS TABLE (unread_count integer)
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO incoming_signals (company_id, user_id, channel, display_name, message_preview, unread_count, is_typing, last_message_at)
  VALUES (
    p_company_id,
    p_user_id,
    COALESCE(NULLIF(p_channel, ''), 'messenger'),
    COALESCE(p_display_name, ''),
    LEFT(COALESCE(p_message_preview, ''), 200),
    1,
    TRUE,
    NOW()
  )
  ON CONFLICT (company_id, user_id)
  DO UPDATE SET
    channel = EXCLUDED.channel,
    display_name = COALESCE(NULLIF(EXCLUDED.display_name, ''), incoming_signals.display_name),
    message_preview = EXCLUDED.message_preview,
    unread_count = incoming_signals.unread_count + 1,
    is_typing = TRUE,
    last_message_at = NOW()
  RETURNING incoming_signals.unread_count INTO unread_count;

  RETURN NEXT;
END;
$$;
