# 🚀 PLAN D'AMÉLIORATION RAG - VERSION FINALE

**Date:** 2025-10-14  
**Score actuel:** 62% (Test Hardcore) | 100% (Test Moyen)  
**Objectif:** 90%+ sur test Hardcore

---

## 📊 DIAGNOSTIC COMPLET

### **Performances actuelles:**
- ⏱️ Temps moyen: **24.8s** (trop lent)
- 🎯 Taux réussite: **77%** (5 timeouts/22)
- 💰 Coût: **$0.0028/requête** (excellent)
- 🧠 Précision: **85%** (3 erreurs données)

### **Goulots d'étranglement identifiés:**
1. **search_sources: 11.9s (48% du temps)** 🔴
2. **endpoint_init: 6.7s (27% du temps)** 🔴
3. **llm_generation: 3.9s (16% du temps)** 🟡
4. **Supabase 8.5x plus lent que MeiliSearch** 🔴

---

## 🎯 PHASE 1: CORRECTIONS DONNÉES (URGENT - 30min)

### ✅ **1.1 Base de données MeiliSearch**

**Corrections à faire:**

| Fichier | Erreur | Correction |
|---------|--------|------------|
| `couches-a-pression-taille-4...` | Prix incohérent | ✅ TOI: Uniformiser 24 000 ou 24 900 |
| `couches-a-pression-taille-6...` | Description "taille 5" | ✅ FAIT: Changé en "taille 6" |

**Vérifications:**
- ✅ Lots 150 pression n'existent PAS (base correcte)
- ✅ Zones livraison correctes dans base
- ✅ Culottes: 150 et 300 disponibles

---

## 🔴 PHASE 2: OPTIMISATION PERFORMANCES (URGENT - 2h)

### **2.1 Réduire temps recherche (gain: -8s)**

**Problème:** Supabase fallback prend 15.4s vs MeiliSearch 1.8s

**Actions:**
```python
# core/universal_rag_engine.py

# Réduire timeout Supabase
SUPABASE_TIMEOUT = 5  # Au lieu de 20s

# Forcer MeiliSearch plus agressivement
MEILISEARCH_MIN_DOCS = 2  # Au lieu de 3

# Désactiver Supabase si MeiliSearch trouve des docs
if meilisearch_docs >= 2:
    skip_supabase = True
```

**Gain attendu:** 15.4s → 7s (-8s)

---

### **2.2 Optimiser endpoint_init (gain: -3s)**

**Problème:** HYDE + cache + prompt = 6.7s

**Actions:**
```python
# app.py

# 1. Paralléliser HYDE et cache check
import asyncio
hyde_task = asyncio.create_task(clarify_request_with_hyde(req.message))
cache_task = asyncio.create_task(redis_cache.get(...))
hyde_result, cache_result = await asyncio.gather(hyde_task, cache_task)

# 2. Désactiver HYDE pour requêtes courtes (<10 mots)
if len(req.message.split()) < 10:
    skip_hyde = True

# 3. Cache prompt en mémoire (déjà fait mais vérifier)
```

**Gain attendu:** 6.7s → 3.5s (-3s)

---

### **2.3 Prompt LLM - Garder 1500-2000 tokens**

**Décision:** NE PAS réduire à 512 tokens (trop agressif)

**Actions:**
```python
# Garder max_tokens actuel
max_tokens = 1024  # OK

# Mais optimiser structure prompt:
# - Supprimer répétitions
# - Contexte plus concis
# - Règles en bullet points
```

**Gain attendu:** Maintien qualité + stabilité temps

---

## 🟡 PHASE 3: AMÉLIORATION MÉMOIRE (IMPORTANT - 4h)

### **3.1 Notepad plus persistant**

**Problème:** Perd "2 lots" au récapitulatif final

**Recherche web nécessaire:**
- GitHub: "conversational memory LLM"
- Reddit: r/LocalLLaMA "context persistence"
- Papers: "long-term memory chatbots"

**Pistes:**
1. **Vector store pour notepad** (Pinecone/Qdrant)
2. **Compression mémoire** (summarization)
3. **Extraction structurée** (JSON forcé)

**Actions:**
```python
# core/conversation_notepad.py

# Option 1: Forcer extraction JSON
def extract_order_details(text):
    prompt = """
    Extrais UNIQUEMENT les infos commande en JSON:
    {
      "quantity": 2,
      "product": "Lot 300 taille 4",
      "zone": "Yopougon"
    }
    """
    # LLM call avec JSON mode

# Option 2: Sauvegarder dans Redis
def persist_to_redis(user_id, data):
    redis.setex(f"order:{user_id}", 3600, json.dumps(data))
```

**Gain attendu:** Mémoire 70% → 95%

---

### **3.2 Vérification stricte zones livraison**

**Solution:** ✅ FAIT - Injection règles dans prompt

```python
# core/universal_rag_engine.py (ligne 635)

delivery_rules = """
⚠️ RÈGLES STRICTES ZONES LIVRAISON:
- Yopougon: 1 500 FCFA (PAS 2 000!)
- Cocody: 1 500 FCFA
- Port-Bouët: 2 000 FCFA
NE CONFONDS PAS!
"""
system_prompt += delivery_rules
```

**Gain attendu:** Erreurs zones 100% → 0%

---

## 🟢 PHASE 4: CACHE SÉMANTIQUE (BONUS - 6h)

### **4.1 Pourquoi cache actuel ne marche pas**

**Problème:** Cache exact match uniquement
- "Bonjour prix taille 4" ≠ "Prix taille 4" ❌
- Première fois = pas de cache ✅ Normal

**Solution: Cache sémantique**

```python
# core/semantic_cache.py (NOUVEAU)

import numpy as np
from sentence_transformers import SentenceTransformer

class SemanticCache:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.cache = {}  # {embedding: response}
        self.threshold = 0.85  # Similarité min
    
    def get(self, query):
        query_emb = self.model.encode(query)
        for cached_emb, response in self.cache.items():
            similarity = cosine_similarity(query_emb, cached_emb)
            if similarity > self.threshold:
                return response
        return None
    
    def set(self, query, response):
        query_emb = self.model.encode(query)
        self.cache[query_emb] = response
```

**Gain attendu:** Cache hit 5% → 40%

---

## 🎯 PHASE 5: SYSTÈME IMAGE INTELLIGENT (IMPLÉMENTÉ ✅)

**Solution:** Botlive = Extracteur silencieux, RAG = Conversationnel

### **Architecture:**
```
Image reçue → Botlive analyse → Retourne JSON structuré → RAG formule réponse
```

### **Fichiers créés:**
1. ✅ `core/image_analyzer.py` - Module analyse images
2. ✅ `core/botlive_integration.py` - Interface Botlive
3. ✅ Intégration dans `universal_rag_engine.py`

### **Fonctionnalités:**
- ✅ Détection automatique type image (produit/paiement)
- ✅ Cache Redis 24h (évite re-analyse)
- ✅ Extraction données structurées
- ✅ Validation paiement (≥2000 FCFA)
- ✅ Description produit détaillée

### **Flux:**
1. Client envoie image
2. `image_analyzer` appelle Botlive
3. Botlive retourne DATA brute (pas de texte)
4. RAG injecte DATA dans prompt
5. LLM formule réponse naturelle

**Gain:** Paiement vérifié automatiquement + Descriptions produits précises

---

## 📈 GAINS ATTENDUS TOTAUX

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| **Temps moyen** | 24.8s | **13s** | -47% 🚀 |
| **Taux réussite** | 77% | **95%** | +18% ✅ |
| **Précision données** | 85% | **100%** | +15% ✅ |
| **Mémoire** | 70% | **95%** | +25% 🧠 |
| **Score global** | 62% | **92%** | +30% 🏆 |

---

## 🚀 ORDRE D'EXÉCUTION

### **AUJOURD'HUI (2h):**
1. ✅ Corriger Taille 4 prix MeiliSearch
2. ✅ Injection règles zones (FAIT)
3. ✅ Optimiser endpoint_init (paralléliser)
4. ✅ Réduire timeout Supabase à 5s

### **DEMAIN (4h):**
5. 🔍 Recherche web mémoire persistante
6. 🧠 Implémenter notepad amélioré
7. 🧪 Tester avec client hardcore

### **CETTE SEMAINE (6h):**
8. 💾 Cache sémantique (si temps)
9. 💰 Système acompte (ton idée)
10. 📊 Monitoring performances

---

## 🎯 CRITÈRES DE SUCCÈS

**Test Hardcore doit atteindre:**
- ✅ 0 timeout (actuellement 5)
- ✅ 95%+ réussite (actuellement 77%)
- ✅ Temps < 15s moyen (actuellement 24.8s)
- ✅ Mémoire parfaite (actuellement 70%)
- ✅ 0 erreur données (actuellement 3)

**Score cible: 90%+** 🏆

---

## 📝 NOTES IMPORTANTES

1. **MeiliSearch déjà prioritaire** ✅
2. **Pas de réduction tokens à 512** ✅
3. **Cache non sémantique = normal** ✅
4. **Données base = cause principale erreurs** ✅
5. **Supabase = goulot principal** 🔴

---

**PROCHAINE ÉTAPE:** Synchroniser fichiers et tester!

```bash
# Copier les modifs
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/universal_rag_engine.py" ~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py

cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/app.py" ~/ZETA_APP/CHATBOT2.0/app.py

# Redémarrer
cd ~/ZETA_APP/CHATBOT2.0
python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload

# Relancer test
python3 test_client_hardcore.py
```

**FIN DU PLAN** 🎯
