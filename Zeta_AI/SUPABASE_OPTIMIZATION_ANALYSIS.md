# 🔍 ANALYSE SUPABASE - Optimisation Performance

## 📊 **DIAGNOSTIC ACTUEL**

### **Problème identifié:**
- ⏱️ Supabase: **15.4s** (62% du temps total)
- 🎯 Objectif: **< 5s** (-68%)

### **Architecture actuelle:**
```python
# supabase_simple.py
1. Génère embedding (sentence-transformers) → ~500ms
2. Fetch TOUS les documents company → ~2-5s
3. Calcule similarité côté Python → ~10-15s
4. Trie et retourne top 5
```

**PROBLÈME MAJEUR:** Calcul similarité côté Python au lieu de pgvector!

---

## 🔬 **RECHERCHE - MEILLEURES PRATIQUES 2024**

### **Source 1: Medium - Optimizing Vector Search at Scale**

#### **Découvertes clés:**

1. **Dimensionnalité:**
   - ❌ Actuel: 768 dimensions (all-mpnet-base-v2)
   - ✅ Recommandé: 384-512 dimensions
   - **Gain:** 50% mémoire, 2x throughput

2. **Index HNSW vs IVFFlat:**
   ```
   HNSW: Meilleur pour < 20M vectors
   - Latence: 28x plus rapide
   - Throughput: 16x meilleur
   - Build time: Plus long
   ```

3. **Float16 vs Float32:**
   ```sql
   -- Migration float16
   ALTER TABLE documents 
   ALTER COLUMN embedding TYPE halfvec(768);
   
   CREATE INDEX ON documents 
   USING hnsw (embedding halfvec_l2_ops);
   ```
   - **Gain:** 50% mémoire, 30% build time

4. **Paramètres optimaux:**
   ```sql
   -- Pour < 1M rows
   lists = rows / 200  (au lieu de rows / 1000)
   probes = lists / 10
   
   -- Pour > 1M rows
   probes = sqrt(lists)
   ```

### **Source 2: DEV.to - Performance Tips pgvector**

#### **Optimisations critiques:**

1. **Utiliser pgvector côté serveur:**
   ```sql
   -- ❌ MAUVAIS (actuel)
   SELECT * FROM documents WHERE company_id = 'xxx';
   -- Puis calcul Python
   
   -- ✅ BON
   SELECT *, embedding <-> '[...]' AS distance
   FROM documents
   WHERE company_id = 'xxx'
   ORDER BY embedding <-> '[...]'
   LIMIT 5;
   ```

2. **EXPLAIN ANALYZE:**
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM documents
   WHERE company_id = 'xxx'
   ORDER BY embedding <-> '[...]'
   LIMIT 5;
   ```

3. **Partitioning:**
   ```sql
   -- Partitionner par company_id
   CREATE TABLE documents_partitioned (
     LIKE documents INCLUDING ALL
   ) PARTITION BY LIST (company_id);
   ```

### **Source 3: Reddit r/Supabase**

#### **Retours production:**

1. **work_mem setting:**
   ```sql
   SET work_mem = '256MB';  -- Par session
   ```

2. **Shared buffers:**
   ```sql
   shared_buffers = 25% of RAM
   ```

3. **Connection pooling:**
   - Utiliser Supavisor (connection pooler)
   - Mode transaction pour vector search

---

## 🎯 **RECOMMANDATIONS PRIORITAIRES**

### **🔴 URGENT - Impact immédiat:**

#### **1. Utiliser pgvector côté serveur (CRITIQUE!)**

**Problème actuel:**
```python
# supabase_simple.py ligne 71
documents = await self._fetch_documents(company_id)  # Fetch TOUT
# Puis calcul Python ligne 89
similarity = self._cosine_similarity(query_embedding, doc_embedding)
```

**Solution:**
```python
async def search_documents_optimized(self, query: str, company_id: str, limit: int = 5):
    """Recherche optimisée avec pgvector côté serveur"""
    
    # 1. Générer embedding
    query_embedding = self.generate_embedding(query)
    
    # 2. Appel RPC Supabase avec pgvector
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.url}/rest/v1/rpc/match_documents",
            headers=self.headers,
            json={
                "query_embedding": query_embedding,
                "match_company_id": company_id,
                "match_threshold": 0.3,
                "match_count": limit
            },
            timeout=aiohttp.ClientTimeout(total=5)  # Timeout 5s
        ) as response:
            results = await response.json()
            return results
```

**Fonction SQL à créer:**
```sql
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(768),
  match_company_id text,
  match_threshold float DEFAULT 0.3,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
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
    AND 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

**Gain attendu:** 15.4s → **3s** (-80%)

---

#### **2. Réduire timeout à 5s**

```python
# Actuel: 20s (trop long!)
timeout=aiohttp.ClientTimeout(total=20)

# Recommandé: 5s
timeout=aiohttp.ClientTimeout(total=5)
```

**Gain:** Force optimisation, évite attentes inutiles

---

#### **3. Créer index HNSW optimisé**

```sql
-- Vérifier index actuel
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'documents';

-- Créer index HNSW optimisé
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Paramètres:
-- m = 16: Nombre de connexions (défaut, bon équilibre)
-- ef_construction = 64: Qualité build (plus haut = meilleur mais plus lent)
```

**Gain:** 2-3x query speed

---

### **🟡 IMPORTANT - Impact moyen terme:**

#### **4. Migration float16**

```sql
-- 1. Créer nouvelle colonne
ALTER TABLE documents 
ADD COLUMN embedding_half halfvec(768);

-- 2. Migrer données
UPDATE documents 
SET embedding_half = embedding::halfvec(768);

-- 3. Créer index float16
CREATE INDEX documents_embedding_half_hnsw_idx
ON documents
USING hnsw (embedding_half halfvec_cosine_ops);

-- 4. Tester performance
-- 5. Si OK, drop ancienne colonne
```

**Gain:** 50% mémoire, 30% build time

---

#### **5. Optimiser modèle embeddings**

**Actuel:**
```python
# 768 dimensions (all-mpnet-base-v2)
self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
```

**Recommandé:**
```python
# 384 dimensions (all-MiniLM-L6-v2)
self.model = SentenceTransformer('all-MiniLM-L6-v2')
```

**Avantages:**
- 50% moins de dimensions
- 2x plus rapide génération
- 90MB vs 420MB
- Qualité: 95% de all-mpnet

**Migration:**
```sql
-- 1. Ajouter colonne 384 dim
ALTER TABLE documents 
ADD COLUMN embedding_384 vector(384);

-- 2. Régénérer embeddings (script Python)
-- 3. Créer index
-- 4. Basculer
```

---

#### **6. Partitioning par company_id**

```sql
-- Créer table partitionnée
CREATE TABLE documents_new (
  id uuid DEFAULT gen_random_uuid(),
  company_id text NOT NULL,
  content text,
  embedding vector(768),
  metadata jsonb,
  created_at timestamptz DEFAULT now()
) PARTITION BY LIST (company_id);

-- Créer partitions pour top companies
CREATE TABLE documents_company_1 
PARTITION OF documents_new 
FOR VALUES IN ('company_1_id');

CREATE TABLE documents_company_2 
PARTITION OF documents_new 
FOR VALUES IN ('company_2_id');

-- Partition par défaut
CREATE TABLE documents_default 
PARTITION OF documents_new DEFAULT;

-- Migrer données
INSERT INTO documents_new SELECT * FROM documents;
```

**Gain:** Query scan réduit, meilleure isolation

---

### **🟢 BONUS - Optimisations avancées:**

#### **7. Caching embeddings**

```python
class EmbeddingCache:
    def __init__(self):
        self.cache = {}  # ou Redis
    
    def get_or_generate(self, text: str):
        if text in self.cache:
            return self.cache[text]
        
        embedding = self.model.encode(text)
        self.cache[text] = embedding
        return embedding
```

---

#### **8. Batch processing**

```python
async def search_batch(self, queries: List[str], company_id: str):
    """Traiter plusieurs requêtes en batch"""
    embeddings = self.model.encode(queries)  # Batch encoding
    
    # Appel RPC batch
    results = await self._batch_search(embeddings, company_id)
    return results
```

---

#### **9. Monitoring pgvector**

```sql
-- Extension pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Queries les plus lentes
SELECT 
  query,
  mean_exec_time,
  calls
FROM pg_stat_statements
WHERE query LIKE '%embedding%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Index usage
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'documents';
```

---

## 📊 **GAINS ATTENDUS**

| Optimisation | Avant | Après | Gain | Priorité |
|--------------|-------|-------|------|----------|
| **pgvector côté serveur** | 15.4s | 3s | -80% | 🔴 URGENT |
| **Timeout 5s** | 20s | 5s | -75% | 🔴 URGENT |
| **Index HNSW** | 3s | 1.5s | -50% | 🔴 URGENT |
| **Float16** | - | - | -50% RAM | 🟡 MOYEN |
| **Modèle 384 dim** | 500ms | 250ms | -50% | 🟡 MOYEN |
| **Partitioning** | 1.5s | 0.8s | -47% | 🟡 MOYEN |
| **TOTAL** | **15.4s** | **< 2s** | **-87%** | 🚀 |

---

## 🚀 **PLAN D'IMPLÉMENTATION**

### **Phase 1: Quick Wins (2h)**
1. ✅ Créer fonction SQL `match_documents`
2. ✅ Modifier `supabase_simple.py` pour utiliser RPC
3. ✅ Réduire timeout à 5s
4. ✅ Tester performance

### **Phase 2: Index Optimization (1h)**
1. ✅ Vérifier index actuel
2. ✅ Créer index HNSW optimisé
3. ✅ EXPLAIN ANALYZE
4. ✅ Mesurer gains

### **Phase 3: Advanced (4h)**
1. 🔄 Migration float16
2. 🔄 Changement modèle 384 dim
3. 🔄 Partitioning
4. 🔄 Monitoring

---

## 🔧 **COMMANDES UTILES**

### **Diagnostic:**
```sql
-- Taille table
SELECT pg_size_pretty(pg_total_relation_size('documents'));

-- Nombre documents par company
SELECT company_id, COUNT(*) 
FROM documents 
GROUP BY company_id;

-- Index existants
\d+ documents
```

### **Performance:**
```sql
-- Activer timing
\timing on

-- Test query
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE company_id = 'xxx'
ORDER BY embedding <=> '[...]'::vector
LIMIT 5;
```

---

## ⚠️ **POINTS D'ATTENTION**

1. **Migration progressive:** Tester sur staging avant prod
2. **Backup:** Sauvegarder avant modifications schema
3. **Monitoring:** Surveiller RAM et CPU pendant migration
4. **Rollback plan:** Garder ancienne implémentation en fallback

---

## 📚 **RESSOURCES**

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Supabase Vector Docs](https://supabase.com/docs/guides/ai/vector-indexes)
- [Medium: Optimizing Vector Search](https://medium.com/@dikhyantkrishnadalai/optimizing-vector-search-at-scale-lessons-from-pgvector-supabase-performance-tuning-ce4ada4ba2ed)
- [DEV.to: pgvector Performance Tips](https://dev.to/shiviyer/performance-tips-for-developers-using-postgres-and-pgvector-l7g)

---

**PROCHAINE ÉTAPE:** Implémenter Phase 1 (Quick Wins) → Gain immédiat -80%! 🚀
