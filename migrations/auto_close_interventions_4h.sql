-- =============================================================================
-- auto_close_interventions_4h.sql
-- pg_cron : ferme automatiquement les interventions ouvertes depuis > 4h
-- Exécuter dans Supabase SQL Editor (pg_cron doit être activé)
-- =============================================================================

-- Active l'extension pg_cron si pas déjà fait
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Supprime l'ancien job s'il existe (idempotent)
SELECT cron.unschedule('auto-close-stale-interventions')
WHERE EXISTS (
    SELECT 1 FROM cron.job WHERE jobname = 'auto-close-stale-interventions'
);

-- Planifie : toutes les 30 minutes
SELECT cron.schedule(
    'auto-close-stale-interventions',
    '*/30 * * * *',
    $$
    UPDATE required_interventions
    SET
        status          = 'resolved',
        resolved_by     = 'auto_expire',
        resolved_at     = now(),
        resolution_note = 'Fermée automatiquement après 4h sans réponse opérateur'
    WHERE
        status IN ('open', 'acknowledged', 'in_progress', 'reopened')
        AND created_at < now() - INTERVAL '4 hours';
    $$
);

-- Vérification : lister les jobs pg_cron actifs
SELECT jobid, jobname, schedule, command, active
FROM cron.job
WHERE jobname = 'auto-close-stale-interventions';
