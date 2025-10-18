-- ============================================================================
-- FONCTION OPTIMISÉE: match_documents
-- Utilise pgvector côté serveur pour calcul similarité
-- Gain attendu: 15.4s → 2-3s (-80%)
-- ============================================================================

-- Supprimer ancienne version si existe
DROP FUNCTION IF EXISTS match_documents(vector, text, double precision, integer);
DROP FUNCTION IF EXISTS match_documents(vector, text, float, integer);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(768),
  match_company_id text,
  match_threshold float DEFAULT 0.3,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float,
  created_at timestamp
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity,
    documents.created_at
  FROM documents
  WHERE 
    documents.company_id = match_company_id
    AND 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- INDEX HNSW OPTIMISÉ
-- Meilleur performance que IVFFlat pour < 20M vectors
-- ============================================================================

-- Vérifier si index existe déjà
DROP INDEX IF EXISTS documents_embedding_hnsw_idx;

-- Créer index HNSW avec paramètres optimisés
CREATE INDEX documents_embedding_hnsw_idx
ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Paramètres:
-- m = 16: Nombre de connexions par nœud (défaut, bon équilibre)
-- ef_construction = 64: Qualité du build (plus haut = meilleur mais plus lent)

-- ============================================================================
-- FONCTION ALTERNATIVE: match_documents_with_metadata_filter
-- Permet filtrage par metadata (ex: category, tags)
-- ============================================================================

-- Supprimer ancienne version si existe
DROP FUNCTION IF EXISTS match_documents_with_filter(vector, text, jsonb, double precision, integer);
DROP FUNCTION IF EXISTS match_documents_with_filter(vector, text, jsonb, float, integer);

CREATE OR REPLACE FUNCTION match_documents_with_filter(
  query_embedding vector(768),
  match_company_id text,
  metadata_filter jsonb DEFAULT '{}'::jsonb,
  match_threshold float DEFAULT 0.3,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 
    documents.company_id = match_company_id
    AND (metadata_filter = '{}'::jsonb OR documents.metadata @> metadata_filter)
    AND 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- MONITORING: Vérifier performance
-- ============================================================================

-- Activer pg_stat_statements si pas déjà fait
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Query pour voir les stats
-- SELECT query, mean_exec_time, calls 
-- FROM pg_stat_statements 
-- WHERE query LIKE '%match_documents%'
-- ORDER BY mean_exec_time DESC;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Exemple 1: Recherche simple
-- SELECT * FROM match_documents(
--   '[0.1, 0.2, ...]'::vector(768),
--   'company_123',
--   0.3,
--   5
-- );

-- Exemple 2: Avec filtre metadata
-- SELECT * FROM match_documents_with_filter(
--   '[0.1, 0.2, ...]'::vector(768),
--   'company_123',
--   '{"category": "produits"}'::jsonb,
--   0.3,
--   5
-- );

-- ============================================================================
-- NOTES D'OPTIMISATION
-- ============================================================================

-- 1. Pour ajuster le seuil de similarité selon vos besoins:
--    - 0.3 = Large (plus de résultats)
--    - 0.5 = Moyen (équilibré)
--    - 0.7 = Strict (très pertinent uniquement)

-- 2. Pour améliorer la vitesse de recherche (trade-off précision):
--    SET hnsw.ef_search = 40;  -- Défaut: 40, Plus haut = plus précis mais plus lent

-- 3. Pour voir l'utilisation de l'index:
--    EXPLAIN ANALYZE SELECT * FROM match_documents(...);

-- 4. Pour reconstruire l'index si dégradé:
--    REINDEX INDEX CONCURRENTLY documents_embedding_hnsw_idx;
