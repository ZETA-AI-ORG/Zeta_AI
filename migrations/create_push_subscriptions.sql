-- Push Subscriptions table for Web Push notifications
-- Stores browser push subscription info per operator/device

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id TEXT NOT NULL,
    operator_id TEXT NOT NULL DEFAULT 'default',
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookup by company
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_company
    ON push_subscriptions(company_id, active);

-- Index for upsert by endpoint
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint
    ON push_subscriptions(endpoint);

-- RLS policies (allow service role full access)
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on push_subscriptions"
    ON push_subscriptions
    FOR ALL
    USING (true)
    WITH CHECK (true);
