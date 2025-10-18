-- ============================================================================
-- MIGRATION 384 DIMENSIONS - Gain 2x vitesse + 50% mémoire
-- Modèle: all-MiniLM-L6-v2 (384 dim) vs all-mpnet-base-v2 (768 dim)
-- ============================================================================

-- AVANTAGES:
-- - Génération embedding: 2x plus rapide
-- - Mémoire: 50% moins
-- - Taille modèle: 90MB vs 420MB
-- - Qualité: 95% de all-mpnet (acceptable pour la plupart des cas)

-- ============================================================================
-- ÉTAPE 1: BACKUP
-- ============================================================================
CREATE TABLE documents_backup_384 AS SELECT * FROM documents;

-- ============================================================================
-- ÉTAPE 2: Ajouter colonne 384 dimensions
-- ============================================================================

-- Float32 (768 → 384)
ALTER TABLE documents 
ADD COLUMN embedding_384 vector(384);

-- Float16 (768 → 384) - RECOMMANDÉ!
ALTER TABLE documents 
ADD COLUMN embedding_384_half halfvec(384);

-- ============================================================================
-- ÉTAPE 3: Régénérer embeddings (SCRIPT PYTHON REQUIS)
-- ============================================================================

-- Ce script doit être exécuté en Python (voir ci-dessous)
-- Il va:
-- 1. Charger all-MiniLM-L6-v2
-- 2. Pour chaque document, générer nouvel embedding 384 dim
-- 3. Mettre à jour la colonne embedding_384_half

-- Vérifier progression
SELECT 
  COUNT(*) as total,
  COUNT(embedding_384_half) as migrated_384,
  ROUND(100.0 * COUNT(embedding_384_half) / COUNT(*), 2) as progress_pct
FROM documents;

-- ============================================================================
-- ÉTAPE 4: Créer index HNSW 384 dimensions
-- ============================================================================

-- Index float16 384 dim (RECOMMANDÉ - 4x plus petit que 768 float32!)
CREATE INDEX documents_embedding_384_half_hnsw_idx
ON documents
USING hnsw (embedding_384_half halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index float32 384 dim (si besoin)
CREATE INDEX documents_embedding_384_hnsw_idx
ON documents
USING hnsw (embedding_384 vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- ÉTAPE 5: Créer fonction RPC 384 dimensions
-- ============================================================================

DROP FUNCTION IF EXISTS match_documents_384(halfvec, text, double precision, integer);
DROP FUNCTION IF EXISTS match_documents_384(halfvec, text, float, integer);

CREATE OR REPLACE FUNCTION match_documents_384(
  query_embedding halfvec(384),
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
    1 - (documents.embedding_384_half <=> query_embedding) AS similarity,
    documents.created_at
  FROM documents
  WHERE 
    documents.company_id = match_company_id
    AND documents.embedding_384_half IS NOT NULL
    AND 1 - (documents.embedding_384_half <=> query_embedding) > match_threshold
  ORDER BY documents.embedding_384_half <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- ÉTAPE 6: Comparer tailles et performance
-- ============================================================================

-- Tailles index
SELECT 
  pg_size_pretty(pg_total_relation_size('documents_embedding_hnsw_idx')) as "768_float32",
  pg_size_pretty(pg_total_relation_size('documents_embedding_half_hnsw_idx')) as "768_float16",
  pg_size_pretty(pg_total_relation_size('documents_embedding_384_hnsw_idx')) as "384_float32",
  pg_size_pretty(pg_total_relation_size('documents_embedding_384_half_hnsw_idx')) as "384_float16";

-- Performance 768 dim
EXPLAIN ANALYZE
SELECT * FROM match_documents(
  array_fill(0.1, ARRAY[768])::vector(768),
  'test_company',
  0.3,
  5
);

-- Performance 384 dim
EXPLAIN ANALYZE
SELECT * FROM match_documents_384(
  array_fill(0.1, ARRAY[384])::halfvec(384),
  'test_company',
  0.3,
  5
);

-- ============================================================================
-- ÉTAPE 7: Test qualité (A/B testing)
-- ============================================================================

-- Comparer résultats 768 vs 384 pour même query
WITH query_768 AS (
  SELECT id, similarity as sim_768
  FROM match_documents(
    array_fill(0.1, ARRAY[768])::vector(768),
    'test_company',
    0.3,
    10
  )
),
query_384 AS (
  SELECT id, similarity as sim_384
  FROM match_documents_384(
    array_fill(0.1, ARRAY[384])::halfvec(384),
    'test_company',
    0.3,
    10
  )
)
SELECT 
  COALESCE(q768.id, q384.id) as doc_id,
  q768.sim_768,
  q384.sim_384,
  ABS(COALESCE(q768.sim_768, 0) - COALESCE(q384.sim_384, 0)) as diff
FROM query_768 q768
FULL OUTER JOIN query_384 q384 ON q768.id = q384.id
ORDER BY diff DESC;

-- ============================================================================
-- ÉTAPE 8: Si OK, supprimer anciennes colonnes (OPTIONNEL)
-- ============================================================================

-- ⚠️ ATTENTION: Irréversible! Faire backup avant!
-- ALTER TABLE documents DROP COLUMN embedding;
-- ALTER TABLE documents DROP COLUMN embedding_half;
-- ALTER TABLE documents RENAME COLUMN embedding_384_half TO embedding;

-- ============================================================================
-- GAINS ATTENDUS
-- ============================================================================
-- Génération embedding: 2x plus rapide (500ms → 250ms)
-- Mémoire index: 75% moins (768 float32 → 384 float16)
-- Taille modèle: 90MB vs 420MB
-- Query speed: Légèrement plus rapide (moins de données)
-- Qualité: 95% de all-mpnet (perte acceptable)

-- ============================================================================
-- ROLLBACK (si problème)
-- ============================================================================
-- DROP INDEX documents_embedding_384_half_hnsw_idx;
-- DROP INDEX documents_embedding_384_hnsw_idx;
-- ALTER TABLE documents DROP COLUMN embedding_384;
-- ALTER TABLE documents DROP COLUMN embedding_384_half;
