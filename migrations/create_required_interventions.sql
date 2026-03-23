-- =============================================================================
-- required_interventions : source de vérité métier du système d'intervention
-- NE PAS EXÉCUTER SANS VALIDATION HUMAINE EXPLICITE
-- =============================================================================

CREATE TABLE IF NOT EXISTS required_interventions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Identité
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'whatsapp',

    -- Taxonomie
    type TEXT NOT NULL CHECK (type IN (
        'explicit_handoff',
        'customer_frustration',
        'bot_confusion',
        'order_blocked',
        'post_order_followup',
        'sav_issue',
        'payment_issue',
        'technical_issue',
        'vip_or_sensitive_case',
        'system_error'
    )),
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN (
        'low', 'normal', 'high', 'critical'
    )),

    -- Détection
    detected_by TEXT NOT NULL DEFAULT 'rule_based' CHECK (detected_by IN (
        'rule_based',
        'intervention_guardian_v1',
        'cooperative_mode',
        'post_recap',
        'system',
        'manual'
    )),
    source_bot TEXT NOT NULL DEFAULT 'botlive' CHECK (source_bot IN (
        'botlive', 'ragbot', 'botliveandrag'
    )),
    confidence REAL,
    reason TEXT NOT NULL DEFAULT '',

    -- Signaux bruts
    signals JSONB NOT NULL DEFAULT '{}',

    -- Contexte
    user_message TEXT DEFAULT '',
    bot_response TEXT DEFAULT '',
    conversation_snippet TEXT DEFAULT '',
    order_state JSONB DEFAULT '{}',

    -- Cycle de vie
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
        'open', 'acknowledged', 'in_progress', 'resolved', 'dismissed', 'reopened'
    )),
    assigned_to TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    resolution_note TEXT DEFAULT '',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index : interventions ouvertes par company (requête principale du frontend)
CREATE INDEX IF NOT EXISTS idx_ri_company_open
    ON required_interventions(company_id, status, created_at DESC)
    WHERE status IN ('open', 'acknowledged', 'in_progress', 'reopened');

-- Index : lookup par user
CREATE INDEX IF NOT EXISTS idx_ri_company_user
    ON required_interventions(company_id, user_id, created_at DESC);

-- Index : priorité critique
CREATE INDEX IF NOT EXISTS idx_ri_priority_critical
    ON required_interventions(company_id, created_at DESC)
    WHERE priority IN ('high', 'critical') AND status IN ('open', 'reopened');

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_ri_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_ri_updated_at
    BEFORE UPDATE ON required_interventions
    FOR EACH ROW EXECUTE FUNCTION update_ri_updated_at();

-- RLS
ALTER TABLE required_interventions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on required_interventions"
    ON required_interventions
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Fonction utilitaire d'upsert (évite les doublons rapprochés pour le même user)
CREATE OR REPLACE FUNCTION upsert_required_intervention(
    p_company_id TEXT,
    p_user_id TEXT,
    p_channel TEXT DEFAULT 'whatsapp',
    p_type TEXT DEFAULT 'explicit_handoff',
    p_priority TEXT DEFAULT 'normal',
    p_detected_by TEXT DEFAULT 'rule_based',
    p_source_bot TEXT DEFAULT 'botlive',
    p_confidence REAL DEFAULT NULL,
    p_reason TEXT DEFAULT '',
    p_signals JSONB DEFAULT '{}',
    p_user_message TEXT DEFAULT '',
    p_bot_response TEXT DEFAULT '',
    p_conversation_snippet TEXT DEFAULT '',
    p_order_state JSONB DEFAULT '{}'
)
RETURNS UUID
LANGUAGE plpgsql AS $$
DECLARE
    existing_id UUID;
    new_id UUID;
BEGIN
    -- Chercher une intervention ouverte récente (< 30 min) pour le même user + type
    SELECT id INTO existing_id
    FROM required_interventions
    WHERE company_id = p_company_id
      AND user_id = p_user_id
      AND type = p_type
      AND status IN ('open', 'acknowledged', 'in_progress', 'reopened')
      AND created_at > now() - interval '30 minutes'
    ORDER BY created_at DESC
    LIMIT 1;

    IF existing_id IS NOT NULL THEN
        -- Mettre à jour l'existante (escalade de priorité si nécessaire)
        UPDATE required_interventions SET
            priority = CASE
                WHEN p_priority = 'critical' THEN 'critical'
                WHEN p_priority = 'high' AND priority NOT IN ('critical') THEN 'high'
                ELSE priority
            END,
            reason = COALESCE(NULLIF(p_reason, ''), reason),
            signals = signals || p_signals,
            user_message = COALESCE(NULLIF(p_user_message, ''), user_message),
            bot_response = COALESCE(NULLIF(p_bot_response, ''), bot_response),
            conversation_snippet = COALESCE(NULLIF(p_conversation_snippet, ''), conversation_snippet),
            updated_at = now()
        WHERE id = existing_id;
        RETURN existing_id;
    ELSE
        INSERT INTO required_interventions (
            company_id, user_id, channel, type, priority,
            detected_by, source_bot, confidence, reason, signals,
            user_message, bot_response, conversation_snippet, order_state
        ) VALUES (
            p_company_id, p_user_id, p_channel, p_type, p_priority,
            p_detected_by, p_source_bot, p_confidence, p_reason, p_signals,
            p_user_message, p_bot_response, p_conversation_snippet, p_order_state
        )
        RETURNING id INTO new_id;
        RETURN new_id;
    END IF;
END;
$$;
