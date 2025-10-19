# 🔍 ANALYSE PERFORMANCE - Optimisation < 6s

## 📊 **Breakdown Actuel (36.4s sans cache)**

```
🕐 DURÉE TOTALE: 36,393ms

📊 ÉTAPES DU PIPELINE:
  ├─ endpoint_init: 7,051ms      (19.4%) 🔴 LENT
  ├─ search_sources: 5,321ms     (14.6%) 🔴 LENT
  ├─ llm_generation: 4,368ms     (12.0%) 🟡 MOYEN
  └─ overhead système: 19,652ms  (54.0%) 🔴 TRÈS LENT
```

---

## 🎯 **CIBLES D'OPTIMISATION**

### **🔴 PRIORITÉ 1: Overhead Système (19.6s → 2s)**

**Problème:** 54% du temps total !

**Détail:**
```
Overhead (19,652ms):
  ├─ Logs verbeux: ~15,000ms     ← 76% de l'overhead !
  ├─ Conversation history: 2,000ms
  ├─ Enhanced memory: 1,000ms
  ├─ Notepad updates: 500ms
  ├─ Checkpoint save: 500ms
  └─ Tracking: 652ms
```

**Solutions:**

#### **1.1 Désactiver logs debug en production**
```python
# Fichier: app.py ou config.py
import logging

if ENVIRONMENT == "production":
    logging.getLogger("database.vector_store_clean_v2").setLevel(logging.WARNING)
    logging.getLogger("core.context_extractor").setLevel(logging.WARNING)
    logging.getLogger("core.delivery_zone_extractor").setLevel(logging.WARNING)
    logging.getLogger("core.universal_rag_engine").setLevel(logging.WARNING)
    logging.getLogger("app").setLevel(logging.INFO)
```
**GAIN ESTIMÉ: -15,000ms (-41%)**

#### **1.2 Asynchroniser les opérations non-critiques**
```python
# Checkpoint, logs, tracking en background
import asyncio

async def save_checkpoint_async(data):
    # Non-bloquant
    pass

# Dans le code principal
asyncio.create_task(save_checkpoint_async(data))
# Continue sans attendre
```
**GAIN ESTIMÉ: -2,000ms (-5.5%)**

#### **1.3 Optimiser conversation history**
```python
# Limiter la taille de l'historique
MAX_HISTORY_MESSAGES = 5  # Au lieu de 10+
MAX_HISTORY_CHARS = 500   # Tronquer si trop long
```
**GAIN ESTIMÉ: -1,000ms (-2.7%)**

**TOTAL PRIORITÉ 1: -18,000ms (-49.5%)**

---

### **🔴 PRIORITÉ 2: Endpoint Init (7s → 2s)**

**Détail:**
```
Endpoint Init (7,051ms):
  ├─ Supabase prompt fetch: 3,450ms  ← 49% !
  ├─ HYDE: 2,000ms                   ← 28%
  ├─ Validation: 500ms
  ├─ Context init: 600ms
  └─ Autres: 501ms
```

**Solutions:**

#### **2.1 Cache local pour prompts**
```python
# Fichier: core/prompt_cache.py
import time

PROMPT_LOCAL_CACHE = {}
CACHE_TTL = 3600  # 1 heure

def get_prompt_cached(company_id):
    cache_key = f"prompt_{company_id}"
    cached = PROMPT_LOCAL_CACHE.get(cache_key)
    
    if cached and time.time() - cached['timestamp'] < CACHE_TTL:
        return cached['prompt']
    
    # Fetch from Supabase
    prompt = fetch_from_supabase(company_id)
    PROMPT_LOCAL_CACHE[cache_key] = {
        'prompt': prompt,
        'timestamp': time.time()
    }
    return prompt
```
**GAIN ESTIMÉ: -3,000ms (-8.2%)**

#### **2.2 Désactiver HYDE pour questions simples**
```python
# Détection question simple
def is_simple_query(query):
    simple_patterns = [
        r'prix\s+\d+',
        r'combien\s+(coute|cout)',
        r'livraison\s+\w+',
        r'contact|telephone|whatsapp'
    ]
    return any(re.search(p, query.lower()) for p in simple_patterns)

# Dans le code
if not is_simple_query(req.message):
    hyde_result = await run_hyde()
else:
    hyde_result = None  # Skip HYDE
```
**GAIN ESTIMÉ: -1,200ms (-3.3%) sur 60% des requêtes**

**TOTAL PRIORITÉ 2: -4,200ms (-11.5%)**

---

### **🔴 PRIORITÉ 3: Search Sources (5.3s → 2.5s)**

**Détail:**
```
Search Sources (5,321ms):
  ├─ MeiliSearch: 3,500ms        ← 66% !
  ├─ Context extraction: 800ms
  ├─ Delivery regex: 400ms
  └─ Filtrage: 621ms
```

**Solutions:**

#### **3.1 Réduire nombre de n-grams**
```python
# Fichier: database/vector_store_clean_v2.py
# Actuel: génère 60+ n-grams
# Optimisé: limiter à 30 n-grams les plus pertinents

def generate_ngrams_optimized(query, max_ngrams=30):
    # Prioriser:
    # 1. Mots-clés produits (couches, taille, lot)
    # 2. Zones (Angré, Marcory, etc.)
    # 3. Bi-grams seulement (pas tri-grams)
    pass
```
**GAIN ESTIMÉ: -1,500ms (-4.1%)**

#### **3.2 Index warming (pré-chargement)**
```python
# Pré-charger les index fréquents en mémoire
import asyncio

async def warm_indexes():
    # Charger products + delivery en mémoire
    await asyncio.gather(
        preload_index("products_*"),
        preload_index("delivery_*")
    )

# Au démarrage de l'app
asyncio.create_task(warm_indexes())
```
**GAIN ESTIMÉ: -800ms (-2.2%)**

#### **3.3 Paralléliser context extraction**
```python
# Extraire contexte en parallèle avec MeiliSearch
async def search_and_extract():
    search_task = asyncio.create_task(meilisearch_query())
    
    # Pendant que MeiliSearch travaille, préparer autres choses
    delivery_task = asyncio.create_task(extract_delivery_zone())
    
    results = await search_task
    delivery = await delivery_task
    
    return results, delivery
```
**GAIN ESTIMÉ: -500ms (-1.4%)**

**TOTAL PRIORITÉ 3: -2,800ms (-7.7%)**

---

### **🟡 PRIORITÉ 4: LLM Generation (4.4s → 3.5s)**

**Détail:**
```
LLM Generation (4,368ms):
  ├─ Groq API call: 3,000ms      ← 69%
  ├─ Parsing thinking: 500ms
  ├─ Tools execution: 600ms
  └─ Response extract: 268ms
```

**Solutions:**

#### **4.1 Streaming LLM (non-bloquant)**
```python
# Retourner la réponse progressivement
async def stream_llm_response():
    async for chunk in groq_client.stream(...):
        yield chunk  # Envoyer au client immédiatement
```
**GAIN PERÇU: Réponse commence à 1s au lieu de 4s**

#### **4.2 Paralléliser parsing**
```python
# Parser thinking pendant que LLM génère
async def generate_and_parse():
    response = ""
    thinking = ""
    
    async for chunk in llm_stream():
        response += chunk
        
        # Parser thinking dès qu'il est complet
        if "</thinking>" in response and not thinking:
            thinking = extract_thinking(response)
            asyncio.create_task(parse_thinking_async(thinking))
```
**GAIN ESTIMÉ: -500ms (-1.4%)**

**TOTAL PRIORITÉ 4: -500ms (-1.4%)**

---

## 📊 **RÉSUMÉ DES GAINS**

| Optimisation | Gain (ms) | Gain (%) | Difficulté |
|--------------|-----------|----------|------------|
| **Logs debug OFF** | -15,000 | -41.2% | 🟢 FACILE |
| **Async non-critiques** | -2,000 | -5.5% | 🟡 MOYEN |
| **Prompt cache local** | -3,000 | -8.2% | 🟢 FACILE |
| **HYDE conditionnel** | -1,200 | -3.3% | 🟢 FACILE |
| **N-grams optimisés** | -1,500 | -4.1% | 🟡 MOYEN |
| **Index warming** | -800 | -2.2% | 🟡 MOYEN |
| **Parallel extract** | -500 | -1.4% | 🟡 MOYEN |
| **History limit** | -1,000 | -2.7% | 🟢 FACILE |
| **LLM parsing parallel** | -500 | -1.4% | 🔴 DIFFICILE |
| **TOTAL** | **-25,500ms** | **-70%** | |

---

## 🎯 **TEMPS CIBLE**

### **Sans cache:**
```
Actuel:   36,393ms
Optimisé: 10,893ms  (-70%)
CIBLE:    <15,000ms ✅
```

### **Avec caches (pondéré):**
```
Actuel:   13,712ms
Optimisé:  4,112ms  (-70%)
CIBLE:     <6,000ms ✅
```

### **Cache hits:**
```
Cache exact:      500ms
Cache sémantique: 1,200ms
FAQ cache:        800ms
CIBLE:            <1,500ms ✅
```

---

## 🚀 **PLAN D'IMPLÉMENTATION**

### **Phase 1: Quick Wins (1-2h)**
1. ✅ Désactiver logs debug
2. ✅ Prompt cache local
3. ✅ HYDE conditionnel
4. ✅ History limit

**GAIN: -20,200ms (-55%)**

### **Phase 2: Optimisations Moyennes (3-4h)**
5. ⏳ Async non-critiques
6. ⏳ N-grams optimisés
7. ⏳ Index warming
8. ⏳ Parallel extract

**GAIN: -4,800ms (-13%)**

### **Phase 3: Optimisations Avancées (1-2j)**
9. ⏳ LLM streaming
10. ⏳ Parallel parsing

**GAIN: -500ms (-1.4%)**

---

## 📝 **MÉTRIQUES À TRACKER**

```python
# Ajouter dans les logs
{
    "request_id": "...",
    "total_time": 10893,
    "breakdown": {
        "endpoint_init": 2051,
        "search_sources": 2521,
        "llm_generation": 3868,
        "overhead": 2453
    },
    "cache_hit": false,
    "optimizations_applied": [
        "logs_disabled",
        "prompt_cached",
        "hyde_skipped"
    ]
}
```

---

## ✅ **VALIDATION**

**Critères de succès:**
- [ ] Temps moyen sans cache < 15s
- [ ] Temps moyen avec cache < 6s
- [ ] Cache hits < 1.5s
- [ ] Overhead < 3s
- [ ] Logs production propres
