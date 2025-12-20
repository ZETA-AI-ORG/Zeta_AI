-- ============================================================================
-- ACTIVE LEARNING SCHEMA - VERSION CORRIGÉE FINALE
-- ============================================================================
-- Date: 2024-12-20
-- Fix: Syntax errors + dollar quoting + function signatures
-- Tables: routing_events, human_labels, rule_candidates, deployed_rules
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- CLEANUP: Drop existing objects
-- ============================================================================

DROP VIEW IF EXISTS public.daily_routing_metrics CASCADE;
DROP VIEW IF EXISTS public.active_rule_candidates CASCADE;
DROP FUNCTION IF EXISTS public.cleanup_expired_rule_candidates() CASCADE;
DROP FUNCTION IF EXISTS public.update_human_labels_weights() CASCADE;
DROP TABLE IF EXISTS public.routing_events CASCADE;
DROP TABLE IF EXISTS public.human_labels CASCADE;
DROP TABLE IF EXISTS public.rule_candidates CASCADE;
DROP TABLE IF EXISTS public.deployed_rules CASCADE;

-- ============================================================================
-- TABLE 1: routing_events
-- ============================================================================

CREATE TABLE public.routing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    user_id TEXT,
    conversation_id TEXT,
    message TEXT NOT NULL,
    final_intent TEXT NOT NULL,
    final_conf DOUBLE PRECISION,
    mode TEXT,
    cache_hit BOOLEAN DEFAULT false,
    latency_ms DOUBLE PRECISION,
    dual_router_mode TEXT,
    dual_router_stage TEXT,
    hyde_used BOOLEAN DEFAULT false,
    hyde_stage TEXT,
    hyde_trigger_reason TEXT,
    hyde_message TEXT,
    smart_hyde_checked BOOLEAN DEFAULT false,
    smart_hyde_should_trigger BOOLEAN DEFAULT false,
    smart_hyde_trigger_reason TEXT,
    guard_applied BOOLEAN DEFAULT false,
    guard_reason TEXT,
    post_validation_applied BOOLEAN DEFAULT false,
    post_validation_reason TEXT,
    human_handoff BOOLEAN DEFAULT false,
    human_handoff_reason TEXT,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_routing_events_company_created 
    ON public.routing_events(company_id, created_at DESC);

CREATE INDEX idx_routing_events_company_intent 
    ON public.routing_events(company_id, final_intent, created_at DESC);

CREATE INDEX idx_routing_events_company_hyde 
    ON public.routing_events(company_id, hyde_used, created_at DESC) 
    WHERE hyde_used = true;

CREATE INDEX idx_routing_events_company_handoff 
    ON public.routing_events(company_id, human_handoff, created_at DESC) 
    WHERE human_handoff = true;

CREATE INDEX idx_routing_events_conversation 
    ON public.routing_events(company_id, conversation_id, created_at DESC);

ALTER TABLE public.routing_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS routing_events_service_role ON public.routing_events;
CREATE POLICY routing_events_service_role ON public.routing_events
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS routing_events_company_select ON public.routing_events;
CREATE POLICY routing_events_company_select ON public.routing_events
    FOR SELECT USING (company_id = current_setting('app.current_company_id', true));

-- ============================================================================
-- TABLE 2: human_labels
-- ============================================================================

CREATE TABLE public.human_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    message_id TEXT,
    original_message TEXT NOT NULL,
    true_intent TEXT NOT NULL,
    resolution_action TEXT,
    notes TEXT,
    agent_id TEXT,
    resolved BOOLEAN DEFAULT false,
    resolution_time_ms INTEGER,
    satisfaction_score INTEGER,
    weight DOUBLE PRECISION DEFAULT 1.0,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb,
    labeled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_human_labels_company_labeled 
    ON public.human_labels(company_id, labeled_at DESC);

CREATE INDEX idx_human_labels_company_intent 
    ON public.human_labels(company_id, true_intent);

CREATE INDEX idx_human_labels_conversation 
    ON public.human_labels(company_id, conversation_id);

CREATE INDEX idx_human_labels_expires 
    ON public.human_labels(expires_at) 
    WHERE expires_at IS NOT NULL;

ALTER TABLE public.human_labels ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS human_labels_service_role ON public.human_labels;
CREATE POLICY human_labels_service_role ON public.human_labels
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS human_labels_company_select ON public.human_labels;
CREATE POLICY human_labels_company_select ON public.human_labels
    FOR SELECT USING (company_id = current_setting('app.current_company_id', true));

-- ============================================================================
-- TABLE 3: rule_candidates
-- ============================================================================

CREATE TABLE public.rule_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    pattern TEXT NOT NULL,
    intent TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    support INTEGER,
    examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    counter_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'proposed',
    proposed_by TEXT DEFAULT 'nightly_analyzer',
    reviewed_by TEXT,
    proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '28 days'),
    activated_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_rule_candidates_company_status 
    ON public.rule_candidates(company_id, status);

CREATE INDEX idx_rule_candidates_company_expires 
    ON public.rule_candidates(company_id, expires_at);

CREATE INDEX idx_rule_candidates_company_intent 
    ON public.rule_candidates(company_id, intent);

CREATE INDEX idx_rule_candidates_status_expires 
    ON public.rule_candidates(status, expires_at);

ALTER TABLE public.rule_candidates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rule_candidates_service_role ON public.rule_candidates;
CREATE POLICY rule_candidates_service_role ON public.rule_candidates
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS rule_candidates_company_select ON public.rule_candidates;
CREATE POLICY rule_candidates_company_select ON public.rule_candidates
    FOR SELECT USING (company_id = current_setting('app.current_company_id', true));

-- ============================================================================
-- TABLE 4: deployed_rules
-- ============================================================================

CREATE TABLE public.deployed_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    environment TEXT NOT NULL,
    version INTEGER NOT NULL,
    rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    accuracy DOUBLE PRECISION,
    hyde_usage DOUBLE PRECISION,
    clarification_rate DOUBLE PRECISION,
    created_by TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX uniq_deployed_rules_company_env_version 
    ON public.deployed_rules(company_id, environment, version);

CREATE INDEX idx_deployed_rules_active 
    ON public.deployed_rules(company_id, environment, activated_at DESC, deactivated_at) 
    WHERE deactivated_at IS NULL;

ALTER TABLE public.deployed_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS deployed_rules_service_role ON public.deployed_rules;
CREATE POLICY deployed_rules_service_role ON public.deployed_rules
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS deployed_rules_company_select ON public.deployed_rules;
CREATE POLICY deployed_rules_company_select ON public.deployed_rules
    FOR SELECT USING (company_id = current_setting('app.current_company_id', true));

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

CREATE FUNCTION public.cleanup_expired_rule_candidates()
RETURNS TABLE(deleted_count INTEGER, company_id TEXT)
LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    WITH deleted AS (
        DELETE FROM public.rule_candidates
        WHERE expires_at < NOW() AND status IN ('proposed', 'rejected')
        RETURNING rule_candidates.company_id
    )
    SELECT 
        COUNT(*)::INTEGER as deleted_count,
        deleted.company_id
    FROM deleted
    GROUP BY deleted.company_id;
END;
$function$;

CREATE FUNCTION public.update_human_labels_weights()
RETURNS INTEGER
LANGUAGE plpgsql
AS $function$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE public.human_labels
    SET weight = CASE
        WHEN labeled_at > NOW() - INTERVAL '28 days' THEN 1.0
        WHEN labeled_at > NOW() - INTERVAL '90 days' THEN 0.5
        WHEN labeled_at > NOW() - INTERVAL '180 days' THEN 0.2
        ELSE 0.1
    END;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$function$;

-- ============================================================================
-- VIEWS
-- ============================================================================

CREATE VIEW public.daily_routing_metrics AS
SELECT 
    company_id,
    DATE(created_at) as date,
    COUNT(*) as total_requests,
    AVG(latency_ms) as avg_latency_ms,
    COUNT(*) FILTER (WHERE cache_hit = true) as cache_hits,
    COUNT(*) FILTER (WHERE hyde_used = true) as hyde_usage,
    COUNT(*) FILTER (WHERE human_handoff = true) as handoffs,
    COUNT(DISTINCT final_intent) as unique_intents
FROM public.routing_events
GROUP BY company_id, DATE(created_at);

CREATE VIEW public.active_rule_candidates AS
SELECT 
    company_id,
    rule_type,
    intent,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM public.rule_candidates
WHERE status = 'proposed' 
  AND expires_at > NOW()
GROUP BY company_id, rule_type, intent;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT ALL ON public.routing_events TO service_role;
GRANT ALL ON public.human_labels TO service_role;
GRANT ALL ON public.rule_candidates TO service_role;
GRANT ALL ON public.deployed_rules TO service_role;
GRANT EXECUTE ON FUNCTION public.cleanup_expired_rule_candidates() TO service_role;
GRANT EXECUTE ON FUNCTION public.update_human_labels_weights() TO service_role;

-- ============================================================================
-- VALIDATION TESTS
-- ============================================================================

DO $test$
DECLARE
    test_id UUID;
BEGIN
    -- Test routing_events
    INSERT INTO public.routing_events (
        company_id, message, final_intent, final_conf
    ) VALUES (
        'test_company', 'test message', 'SALUT', 0.95
    ) RETURNING id INTO test_id;
    RAISE NOTICE 'routing_events: OK (id=%)', test_id;
    
    -- Test human_labels
    INSERT INTO public.human_labels (
        company_id, conversation_id, original_message, true_intent
    ) VALUES (
        'test_company', 'conv_123', 'test message', 'SALUT'
    ) RETURNING id INTO test_id;
    RAISE NOTICE 'human_labels: OK (id=%)', test_id;
    
    -- Test rule_candidates
    INSERT INTO public.rule_candidates (
        company_id, rule_type, pattern, intent
    ) VALUES (
        'test_company', 'lexical_guard', 'où trouvez', 'INFO_GENERALE'
    ) RETURNING id INTO test_id;
    RAISE NOTICE 'rule_candidates: OK (id=%)', test_id;
    
    -- Test deployed_rules
    INSERT INTO public.deployed_rules (
        company_id, environment, version
    ) VALUES (
        'test_company', 'staging', 1
    ) RETURNING id INTO test_id;
    RAISE NOTICE 'deployed_rules: OK (id=%)', test_id;
    
    -- Test functions
    PERFORM public.update_human_labels_weights();
    RAISE NOTICE 'update_human_labels_weights: OK';
    
    -- Cleanup
    DELETE FROM public.routing_events WHERE company_id = 'test_company';
    DELETE FROM public.human_labels WHERE company_id = 'test_company';
    DELETE FROM public.rule_candidates WHERE company_id = 'test_company';
    DELETE FROM public.deployed_rules WHERE company_id = 'test_company';
    
    RAISE NOTICE '✅ ALL TESTS PASSED';
    
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION '❌ TEST FAILED: %', SQLERRM;
END;
$test$;