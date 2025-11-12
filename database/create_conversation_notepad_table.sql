-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: conversation_notepad
-- Description: Stocke les données de commande en cours avec auto-expiration 7 jours
-- Sécurité: RLS activé, données liées à user_id
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Créer la table
CREATE TABLE IF NOT EXISTS public.conversation_notepad (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Index pour performance
    CONSTRAINT unique_user_company UNIQUE (user_id, company_id)
);

-- 2. Créer index pour requêtes rapides
CREATE INDEX IF NOT EXISTS idx_notepad_user_company ON public.conversation_notepad(user_id, company_id);
CREATE INDEX IF NOT EXISTS idx_notepad_expires_at ON public.conversation_notepad(expires_at);
CREATE INDEX IF NOT EXISTS idx_notepad_updated_at ON public.conversation_notepad(updated_at DESC);

-- 3. Activer Row Level Security (RLS)
ALTER TABLE public.conversation_notepad ENABLE ROW LEVEL SECURITY;

-- 4. Politique RLS: Les utilisateurs ne peuvent voir que leurs propres données
CREATE POLICY "Users can view own notepad"
    ON public.conversation_notepad
    FOR SELECT
    USING (auth.uid()::text = user_id OR auth.role() = 'service_role');

CREATE POLICY "Users can insert own notepad"
    ON public.conversation_notepad
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id OR auth.role() = 'service_role');

CREATE POLICY "Users can update own notepad"
    ON public.conversation_notepad
    FOR UPDATE
    USING (auth.uid()::text = user_id OR auth.role() = 'service_role');

CREATE POLICY "Users can delete own notepad"
    ON public.conversation_notepad
    FOR DELETE
    USING (auth.uid()::text = user_id OR auth.role() = 'service_role');

-- 5. Fonction trigger pour auto-update updated_at
CREATE OR REPLACE FUNCTION update_notepad_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_notepad_timestamp
    BEFORE UPDATE ON public.conversation_notepad
    FOR EACH ROW
    EXECUTE FUNCTION update_notepad_updated_at();

-- 6. Fonction pour cleanup automatique (à appeler via cron)
CREATE OR REPLACE FUNCTION cleanup_expired_notepads()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.conversation_notepad
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up % expired notepads', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Commentaires pour documentation
COMMENT ON TABLE public.conversation_notepad IS 'Stocke les données de commande en cours avec expiration automatique après 7 jours';
COMMENT ON COLUMN public.conversation_notepad.user_id IS 'ID utilisateur (peut être lié à auth.users ou anonyme)';
COMMENT ON COLUMN public.conversation_notepad.company_id IS 'ID entreprise (TEXT, compatible avec company_rag_configs)';
COMMENT ON COLUMN public.conversation_notepad.data IS 'Données JSON du notepad (produits, zone, téléphone, etc.)';
COMMENT ON COLUMN public.conversation_notepad.expires_at IS 'Date expiration automatique (created_at + 7 jours)';

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSTRUCTIONS D'UTILISATION
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Exécuter ce script dans l'éditeur SQL Supabase
-- 2. Configurer un cron job pour cleanup automatique (optionnel):
--    SELECT cron.schedule(
--        'cleanup-expired-notepads',
--        '0 2 * * *',  -- Tous les jours à 2h du matin
--        $$ SELECT cleanup_expired_notepads(); $$
--    );

-- 3. Vérifier la table:
--    SELECT * FROM public.conversation_notepad LIMIT 10;

-- 4. Tester cleanup manuel:
--    SELECT cleanup_expired_notepads();
