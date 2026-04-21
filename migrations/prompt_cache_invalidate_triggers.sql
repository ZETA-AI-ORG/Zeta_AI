-- ════════════════════════════════════════════════════════════════════════════
-- 🔔 TRIGGERS pg_notify → INVALIDATION CACHE PROMPTS ZETA AI
-- ════════════════════════════════════════════════════════════════════════════
-- À exécuter UNE SEULE FOIS dans le SQL editor Supabase (ou via psql CLI).
--
-- Effet :
--   Chaque UPDATE/INSERT sur les tables suivantes déclenche NOTIFY sur le
--   channel 'prompt_cache_invalidate' avec un payload JSON.
--   Le listener Python (core/prompt_cache_listener.py) reçoit la notif et
--   invalide les 3 couches de cache (Redis + in-memory).
--
-- Tables concernées :
--   - company_rag_configs : changement de config marchand (rag_behavior, etc.)
--   - prompt_bots         : changement de template Amanda / Jessica
--   - subscriptions       : changement de plan ou de boost
--
-- Rollback : voir section DROP en bas du fichier.
-- ════════════════════════════════════════════════════════════════════════════


-- ─── 1. Fonction générique : NOTIFY avec payload JSON ────────────────────────
CREATE OR REPLACE FUNCTION zeta_notify_prompt_cache_invalidate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    payload jsonb;
    v_company_id text;
    v_bot_type   text;
BEGIN
    -- company_id : présent sur company_rag_configs et subscriptions
    BEGIN
        v_company_id := COALESCE(
            NEW.company_id::text,
            OLD.company_id::text,
            NULL
        );
    EXCEPTION WHEN undefined_column THEN
        v_company_id := NULL;
    END;

    -- bot_type : présent uniquement sur prompt_bots
    BEGIN
        v_bot_type := COALESCE(
            NEW.bot_type::text,
            OLD.bot_type::text,
            NULL
        );
    EXCEPTION WHEN undefined_column THEN
        v_bot_type := NULL;
    END;

    payload := jsonb_build_object(
        'table',     TG_TABLE_NAME,
        'op',        TG_OP,
        'company_id', v_company_id,
        'bot_type',  v_bot_type,
        'ts',        extract(epoch from now())
    );

    -- Limite 8000 bytes : on ne sérialise que le payload minimal
    PERFORM pg_notify('prompt_cache_invalidate', payload::text);
    RETURN COALESCE(NEW, OLD);
END;
$$;


-- ─── 2. Triggers sur company_rag_configs ─────────────────────────────────────
DROP TRIGGER IF EXISTS trg_notify_prompt_cache_company_rag_configs
    ON public.company_rag_configs;

CREATE TRIGGER trg_notify_prompt_cache_company_rag_configs
AFTER INSERT OR UPDATE OR DELETE
ON public.company_rag_configs
FOR EACH ROW
EXECUTE FUNCTION zeta_notify_prompt_cache_invalidate();


-- ─── 3. Triggers sur prompt_bots ─────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_notify_prompt_cache_prompt_bots
    ON public.prompt_bots;

CREATE TRIGGER trg_notify_prompt_cache_prompt_bots
AFTER INSERT OR UPDATE OR DELETE
ON public.prompt_bots
FOR EACH ROW
EXECUTE FUNCTION zeta_notify_prompt_cache_invalidate();


-- ─── 4. Triggers sur subscriptions ───────────────────────────────────────────
--   Un changement de plan ou de boost impacte bot_registry (Amanda/Jessica
--   choisissent un modèle différent) → on invalide.
DROP TRIGGER IF EXISTS trg_notify_prompt_cache_subscriptions
    ON public.subscriptions;

CREATE TRIGGER trg_notify_prompt_cache_subscriptions
AFTER INSERT OR UPDATE OR DELETE
ON public.subscriptions
FOR EACH ROW
EXECUTE FUNCTION zeta_notify_prompt_cache_invalidate();


-- ─── 5. TEST MANUEL ──────────────────────────────────────────────────────────
-- Depuis psql (ou SQL editor Supabase), écouter :
--     LISTEN prompt_cache_invalidate;
-- Puis faire un UPDATE factice :
--     UPDATE company_rag_configs SET updated_at = now()
--     WHERE company_id = 'test_company';
-- Tu devrais recevoir :
--     Asynchronous notification "prompt_cache_invalidate"
--     with payload "{"table":"company_rag_configs","op":"UPDATE","company_id":"test_company","bot_type":null,"ts":...}"


-- ═══ ROLLBACK (si besoin de retirer) ═════════════════════════════════════════
-- DROP TRIGGER IF EXISTS trg_notify_prompt_cache_company_rag_configs
--     ON public.company_rag_configs;
-- DROP TRIGGER IF EXISTS trg_notify_prompt_cache_prompt_bots
--     ON public.prompt_bots;
-- DROP TRIGGER IF EXISTS trg_notify_prompt_cache_subscriptions
--     ON public.subscriptions;
-- DROP FUNCTION IF EXISTS zeta_notify_prompt_cache_invalidate();
