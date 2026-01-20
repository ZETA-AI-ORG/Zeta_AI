-- Table pour logger tous les prompts envoyés au LLM
CREATE TABLE IF NOT EXISTS prompt_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    full_prompt TEXT NOT NULL,
    context_used TEXT,
    conversation_history TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    prompt_length INTEGER,
    context_length INTEGER,
    history_length INTEGER,
    model_used TEXT,
    response_generated TEXT,
    response_time_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index pour optimiser les requêtes par company_id et timestamp
CREATE INDEX IF NOT EXISTS idx_prompt_logs_company_timestamp 
ON prompt_logs(company_id, timestamp DESC);

-- Index pour recherche par user_query
CREATE INDEX IF NOT EXISTS idx_prompt_logs_query 
ON prompt_logs USING gin(to_tsvector('french', user_query));

-- Politique RLS pour sécuriser l'accès
ALTER TABLE prompt_logs ENABLE ROW LEVEL SECURITY;

-- Politique: Accès complet pour le service role
CREATE POLICY "Service role full access" ON prompt_logs
FOR ALL USING (auth.role() = 'service_role');

-- Politique: Les utilisateurs peuvent voir leurs propres logs
CREATE POLICY "Users can view own logs" ON prompt_logs
FOR SELECT USING (company_id = current_setting('app.current_company_id', true));

-- Commentaires pour documentation
COMMENT ON TABLE prompt_logs IS 'Logs de tous les prompts envoyés au LLM pour debugging et analyse';
COMMENT ON COLUMN prompt_logs.company_id IS 'ID de l''entreprise associée';
COMMENT ON COLUMN prompt_logs.user_query IS 'Question originale de l''utilisateur';
COMMENT ON COLUMN prompt_logs.full_prompt IS 'Prompt complet envoyé au LLM';
COMMENT ON COLUMN prompt_logs.context_used IS 'Contexte RAG utilisé';
COMMENT ON COLUMN prompt_logs.conversation_history IS 'Historique de conversation inclus';
