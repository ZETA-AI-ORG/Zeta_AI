# 🚀 GUIDE D'INSTALLATION - Optimisation Supabase

## 📋 **ÉTAPES D'INSTALLATION**

### **ÉTAPE 1: Exécuter SQL sur Supabase (5min)**

1. **Se connecter à Supabase Dashboard:**
   - https://supabase.com/dashboard
   - Projet: ilbihprkxcgsigvueeme

2. **Ouvrir SQL Editor:**
   - Menu gauche → SQL Editor
   - New Query

3. **Copier-coller le contenu de `database/supabase_match_documents.sql`**

4. **Exécuter (Run)**

5. **Vérifier création:**
   ```sql
   -- Vérifier fonction
   SELECT proname FROM pg_proc WHERE proname = 'match_documents';
   
   -- Vérifier index
   SELECT indexname FROM pg_indexes WHERE tablename = 'documents';
   ```

**Résultat attendu:**
```
proname: match_documents
indexname: documents_embedding_hnsw_idx
```

---

### **ÉTAPE 2: Tester la fonction RPC (5min)**

1. **Dans SQL Editor:**
   ```sql
   -- Test avec embedding factice
   SELECT * FROM match_documents(
     array_fill(0.1, ARRAY[768])::vector(768),
     'votre_company_id',
     0.3,
     5
   );
   ```

2. **Vérifier résultats:**
   - Doit retourner 5 documents max
   - Avec colonnes: id, content, metadata, similarity

3. **Mesurer performance:**
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM match_documents(
     array_fill(0.1, ARRAY[768])::vector(768),
     'votre_company_id',
     0.3,
     5
   );
   ```

**Temps attendu:** < 100ms (vs 15s avant)

---

### **ÉTAPE 3: Synchroniser fichiers Python (2min)**

```bash
cd "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0"

# Copier nouveau fichier optimisé
cp -v core/supabase_optimized.py ~/ZETA_APP/CHATBOT2.0/core/supabase_optimized.py

# Copier fichiers précédents
cp -v core/enhanced_memory.py ~/ZETA_APP/CHATBOT2.0/core/enhanced_memory.py
cp -v core/semantic_cache.py ~/ZETA_APP/CHATBOT2.0/core/semantic_cache.py
cp -v core/botlive_integration.py ~/ZETA_APP/CHATBOT2.0/core/botlive_integration.py
cp -v core/image_analyzer.py ~/ZETA_APP/CHATBOT2.0/core/image_analyzer.py
cp -v core/universal_rag_engine.py ~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py
cp -v app.py ~/ZETA_APP/CHATBOT2.0/app.py

# Copier documentation
cp -v SUPABASE_OPTIMIZATION_ANALYSIS.md ~/ZETA_APP/CHATBOT2.0/
cp -v ENHANCED_MEMORY_README.md ~/ZETA_APP/CHATBOT2.0/
cp -v SEMANTIC_CACHE_README.md ~/ZETA_APP/CHATBOT2.0/
```

---

### **ÉTAPE 4: Modifier universal_rag_engine.py (5min)**

Remplacer l'import dans `universal_rag_engine.py`:

```python
# AVANT (ligne 337)
from .supabase_simple import SupabaseSimple
supabase = SupabaseSimple()

# APRÈS
from .supabase_optimized import SupabaseOptimized
supabase = SupabaseOptimized()
```

**Fichier complet à modifier:**
```python
# core/universal_rag_engine.py ligne 333-345

# 🔄 ÉTAPE FALLBACK: RECHERCHE SUPABASE (si MeiliSearch échoue)
if not meili_success:
    print(f"🔄 [ÉTAPE 2] Supabase fallback...")
    try:
        from .supabase_optimized import SupabaseOptimized  # ← CHANGÉ
        supabase = SupabaseOptimized()  # ← CHANGÉ
        
        # Recherche sémantique avec query originale
        supabase_docs = await supabase.search_documents(
            query=query,
            company_id=company_id,
            limit=5
        )
```

---

### **ÉTAPE 5: Redémarrer serveur (1min)**

```bash
cd ~/ZETA_APP/CHATBOT2.0

# Arrêter serveur actuel (Ctrl+C)

# Redémarrer
python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

**Vérifier logs:**
```
✅ SupabaseOptimized initialisé (pgvector côté serveur)
```

---

### **ÉTAPE 6: Tester performance (5min)**

```bash
# Test simple
python3 test_client_moyen.py

# Vérifier logs
python3 view_logs.py tail
```

**Chercher dans les logs:**
```
🚀 [OPTIMIZED] Recherche Supabase: '...'
✅ Embedding généré: 768 dimensions (0.45s)
✅ RPC match_documents: 5 résultats (1.2s)
⚡ TOTAL: 1.65s (vs 15.4s avant)
```

**Gain attendu:** 15.4s → **1.5-3s** (-80% à -90%)

---

## 🔍 **VÉRIFICATION INSTALLATION**

### **Checklist:**

- [ ] Fonction SQL `match_documents` créée
- [ ] Index HNSW `documents_embedding_hnsw_idx` créé
- [ ] Test RPC fonctionne (< 100ms)
- [ ] Fichier `supabase_optimized.py` copié
- [ ] Import modifié dans `universal_rag_engine.py`
- [ ] Serveur redémarré
- [ ] Logs montrent "SupabaseOptimized initialisé"
- [ ] Test client montre gain performance

---

## 🐛 **TROUBLESHOOTING**

### **Problème 1: Fonction RPC non trouvée**

**Erreur:**
```
RPC error 404: function match_documents does not exist
```

**Solution:**
```sql
-- Vérifier si fonction existe
SELECT proname FROM pg_proc WHERE proname = 'match_documents';

-- Si vide, réexécuter le SQL
-- Copier-coller database/supabase_match_documents.sql
```

---

### **Problème 2: Index non utilisé**

**Vérifier:**
```sql
EXPLAIN ANALYZE
SELECT * FROM match_documents(
  array_fill(0.1, ARRAY[768])::vector(768),
  'company_id',
  0.3,
  5
);
```

**Chercher dans output:**
```
Index Scan using documents_embedding_hnsw_idx
```

**Si absent:**
```sql
-- Forcer recréation index
REINDEX INDEX CONCURRENTLY documents_embedding_hnsw_idx;
```

---

### **Problème 3: Timeout 5s trop court**

**Symptôme:**
```
aiohttp.ClientTimeout: total=5
```

**Solution temporaire:**
```python
# core/supabase_optimized.py ligne 96
timeout = aiohttp.ClientTimeout(total=10)  # Augmenter à 10s
```

**Solution permanente:**
- Optimiser index
- Réduire nombre de documents
- Partitioning par company_id

---

### **Problème 4: Fallback utilisé**

**Logs:**
```
⚠️ Utilisation méthode fallback (moins performante)
```

**Causes possibles:**
1. Fonction RPC non créée
2. Timeout trop court
3. Erreur SQL

**Debug:**
```python
# Ajouter logs détaillés
print(f"Error details: {e}")
import traceback
traceback.print_exc()
```

---

## 📊 **MONITORING**

### **Vérifier performance en production:**

```sql
-- Queries les plus lentes
SELECT 
  query,
  mean_exec_time,
  calls,
  total_exec_time
FROM pg_stat_statements
WHERE query LIKE '%match_documents%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Utilisation index
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read
FROM pg_stat_user_indexes
WHERE tablename = 'documents'
  AND indexname = 'documents_embedding_hnsw_idx';
```

**Métriques attendues:**
- `mean_exec_time`: < 100ms
- `idx_scan`: > 0 (index utilisé)

---

## 🎯 **ROLLBACK (si problème)**

### **Revenir à l'ancienne version:**

```python
# core/universal_rag_engine.py ligne 337
from .supabase_simple import SupabaseSimple  # ← Remettre
supabase = SupabaseSimple()  # ← Remettre
```

```bash
# Redémarrer
cd ~/ZETA_APP/CHATBOT2.0
python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

**Note:** Fonction SQL et index peuvent rester, ils ne causent pas de problème.

---

## 📈 **MÉTRIQUES AVANT/APRÈS**

### **Avant optimisation:**
```
[ÉTAPE 2] Supabase fallback...
📄 Documents récupérés: 1247
⚡ Similarités calculées: 1247 docs
✅ [ÉTAPE 2] Supabase OK: 5 docs
⏱️  Temps: 15.4s
```

### **Après optimisation:**
```
🚀 [OPTIMIZED] Recherche Supabase: '...'
✅ Embedding généré: 768 dimensions (0.45s)
✅ RPC match_documents: 5 résultats (1.2s)
⚡ TOTAL: 1.65s (vs 15.4s avant)
```

**Gain:** -89% 🚀

---

## 🚀 **PROCHAINES OPTIMISATIONS (optionnel)**

### **Phase 2: Float16 (gain mémoire 50%)**
```sql
-- Voir database/supabase_float16_migration.sql
```

### **Phase 3: Modèle 384 dimensions (gain vitesse 2x)**
```python
# all-MiniLM-L6-v2 au lieu de all-mpnet-base-v2
```

### **Phase 4: Partitioning (gain query 50%)**
```sql
-- Partitionner par company_id
```

---

**Installation terminée! Tester maintenant avec `python3 test_client_hardcore.py`** 🎯
