-- ============================================================================
-- PARTITIONING PAR COMPANY_ID - Gain 50% query speed
-- CRITIQUE pour 100+ entreprises
-- ============================================================================

-- STRATÉGIE: Hash partitioning (meilleur pour distribution égale)
-- Alternative: List partitioning (si peu d'entreprises VIP)

-- ============================================================================
-- ÉTAPE 1: BACKUP COMPLET
-- ============================================================================
CREATE TABLE documents_backup_partition AS SELECT * FROM documents;

-- ============================================================================
-- ÉTAPE 2: Créer table partitionnée
-- ============================================================================

-- Renommer ancienne table
ALTER TABLE documents RENAME TO documents_old;

-- Créer nouvelle table partitionnée (HASH pour 100+ companies)
CREATE TABLE documents (
  id bigint GENERATED ALWAYS AS IDENTITY,
  company_id text NOT NULL,
  content text,
  embedding vector(768),
  embedding_half halfvec(768),
  metadata jsonb,
  created_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now()
) PARTITION BY HASH (company_id);

-- ============================================================================
-- ÉTAPE 3: Créer partitions (16 partitions = bon équilibre)
-- ============================================================================

-- Pour 100+ companies, 16 partitions donnent ~6-7 companies par partition
CREATE TABLE documents_p0 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE documents_p1 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE documents_p2 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE documents_p3 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE documents_p4 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE documents_p5 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE documents_p6 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE documents_p7 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE documents_p8 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE documents_p9 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE documents_p10 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE documents_p11 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE documents_p12 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE documents_p13 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE documents_p14 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE documents_p15 PARTITION OF documents FOR VALUES WITH (MODULUS 16, REMAINDER 15);

-- ============================================================================
-- ÉTAPE 4: Créer index sur CHAQUE partition
-- ============================================================================

-- Index HNSW sur chaque partition (parallélisable!)
DO $$
DECLARE
  partition_name text;
BEGIN
  FOR i IN 0..15 LOOP
    partition_name := 'documents_p' || i;
    
    -- Index vector float32
    EXECUTE format('
      CREATE INDEX %I_embedding_hnsw_idx
      ON %I
      USING hnsw (embedding vector_cosine_ops)
      WITH (m = 16, ef_construction = 64)
    ', partition_name, partition_name);
    
    -- Index vector float16 (si utilisé)
    EXECUTE format('
      CREATE INDEX %I_embedding_half_hnsw_idx
      ON %I
      USING hnsw (embedding_half halfvec_cosine_ops)
      WITH (m = 16, ef_construction = 64)
    ', partition_name, partition_name);
    
    -- Index company_id
    EXECUTE format('
      CREATE INDEX %I_company_id_idx
      ON %I (company_id)
    ', partition_name, partition_name);
    
    RAISE NOTICE 'Partition % indexed', partition_name;
  END LOOP;
END $$;

-- ============================================================================
-- ÉTAPE 5: Migrer données
-- ============================================================================

-- Insérer depuis ancienne table
INSERT INTO documents (company_id, content, embedding, embedding_half, metadata, created_at, updated_at)
SELECT company_id, content, embedding, embedding_half, metadata, created_at, updated_at
FROM documents_old;

-- Vérifier migration
SELECT 
  'documents_old' as source,
  COUNT(*) as count
FROM documents_old
UNION ALL
SELECT 
  'documents_new' as source,
  COUNT(*) as count
FROM documents;

-- ============================================================================
-- ÉTAPE 6: Vérifier distribution
-- ============================================================================

SELECT 
  tableoid::regclass as partition,
  COUNT(*) as rows,
  COUNT(DISTINCT company_id) as companies,
  pg_size_pretty(pg_total_relation_size(tableoid)) as size
FROM documents
GROUP BY tableoid
ORDER BY partition;

-- ============================================================================
-- ÉTAPE 7: Tester performance
-- ============================================================================

-- Test AVANT partitioning
EXPLAIN ANALYZE
SELECT * FROM documents_old
WHERE company_id = 'test_company'
ORDER BY embedding <=> '[0.1, ...]'::vector(768)
LIMIT 5;

-- Test APRÈS partitioning
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE company_id = 'test_company'
ORDER BY embedding <=> '[0.1, ...]'::vector(768)
LIMIT 5;

-- ============================================================================
-- ÉTAPE 8: Mettre à jour fonction RPC (si nécessaire)
-- ============================================================================

-- La fonction match_documents existante fonctionne automatiquement!
-- PostgreSQL route vers la bonne partition

-- Test
SELECT * FROM match_documents(
  array_fill(0.1, ARRAY[768])::vector(768),
  'test_company',
  0.3,
  5
);

-- ============================================================================
-- ÉTAPE 9: Nettoyer (après validation)
-- ============================================================================

-- DROP TABLE documents_old;
-- DROP TABLE documents_backup_partition;

-- ============================================================================
-- GAINS ATTENDUS
-- ============================================================================
-- Query speed: -50% (scan seulement 1/16 des données)
-- Index size: Identique total, mais distribué
-- Maintenance: Plus facile (rebuild partition par partition)
-- Scalabilité: Excellente (ajouter partitions si besoin)

-- ============================================================================
-- MONITORING
-- ============================================================================

-- Voir quelle partition est utilisée
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM documents
WHERE company_id = 'specific_company'
LIMIT 10;

-- Statistiques par partition
SELECT 
  schemaname,
  tablename,
  n_live_tup as rows,
  n_dead_tup as dead_rows,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
WHERE tablename LIKE 'documents_p%'
ORDER BY tablename;

-- ============================================================================
-- ROLLBACK (si problème)
-- ============================================================================
-- DROP TABLE documents CASCADE;
-- ALTER TABLE documents_old RENAME TO documents;
-- -- Recréer index
-- CREATE INDEX documents_embedding_hnsw_idx ON documents USING hnsw (embedding vector_cosine_ops);
