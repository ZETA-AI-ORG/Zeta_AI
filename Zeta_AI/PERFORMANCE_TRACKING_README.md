# ⏱️ SYSTÈME DE TRACKING PERFORMANCE RAG

## 🎯 OBJECTIF

Mesurer en temps réel:
- ✅ **Temps d'exécution** de chaque étape du pipeline RAG
- ✅ **Tokens réels** utilisés par le LLM (70B/8B)
- ✅ **Coût exact** par requête en USD
- ✅ **Affichage en ROUGE** dans les logs serveur

## 📦 FICHIERS CRÉÉS

### 1. `core/rag_performance_tracker.py`
Système de tracking complet avec:
- Mesure temps de chaque étape
- Calcul coûts réels par modèle LLM
- Affichage résumé en ROUGE

### 2. `core/llm_client.py` (MODIFIÉ)
- Extraction tokens usage de l'API Groq
- Retourne `{response, usage, model}`

### 3. `core/universal_rag_engine.py` (MODIFIÉ)
- Intégration tracker dans chaque étape
- Passage request_id

### 4. `app.py` (MODIFIÉ)
- Initialisation tracker au début
- Affichage résumé ROUGE à la fin
- Sauvegarde performance dans logs JSON

## 🚀 UTILISATION

### **Automatique**
Le système fonctionne automatiquement pour chaque requête `/chat`.

### **Résultat dans les logs serveur:**

```
================================================================================
⏱️  PERFORMANCE TRACKING - a1b2c3d4
================================================================================
🕐 DURÉE TOTALE: 11450.23ms (11.45s)

📊 ÉTAPES DU PIPELINE:
  ├─ endpoint_init: 2.15ms
  ├─ search_sources: 3245.67ms | {'documents_found': 5}
  ├─ llm_generation: 7892.34ms | {'prompt_length': 2345}
  └─ response_processing: 310.07ms

🤖 USAGE LLM:
  ├─ Modèle: llama-3.3-70b-versatile
  ├─ Tokens prompt: 2,345
  ├─ Tokens completion: 156
  ├─ Tokens total: 2,501
  ├─ Coût prompt: $0.001384
  ├─ Coût completion: $0.000123
  └─ COÛT TOTAL: $0.001507

📈 ANALYSE:
  ├─ Étape la plus lente: llm_generation (7892.34ms)
  └─ Overhead système: 0.00ms
================================================================================
```

## 💰 COÛTS PAR MODÈLE

| Modèle | Input ($/1M tokens) | Output ($/1M tokens) |
|--------|---------------------|----------------------|
| **llama-3.3-70b-versatile** | $0.59 | $0.79 |
| **llama-3.1-8b-instant** | $0.05 | $0.08 |
| **openai/gpt-oss-120b** | $0.50 | $0.70 |

## 📊 LOGS JSON

Les performances sont aussi sauvegardées dans les logs JSON:

```json
{
  "request_id": "a1b2c3d4",
  "metadata": {
    "processing_time_ms": 11450.23,
    "performance": {
      "total_duration_ms": 11450.23,
      "steps": [
        {
          "name": "search_sources",
          "duration_ms": 3245.67,
          "metadata": {"documents_found": 5}
        },
        {
          "name": "llm_generation",
          "duration_ms": 7892.34
        }
      ],
      "llm_usage": {
        "model": "llama-3.3-70b-versatile",
        "prompt_tokens": 2345,
        "completion_tokens": 156,
        "total_tokens": 2501,
        "total_cost_usd": 0.001507
      }
    }
  }
}
```

## 🔍 CONSULTER LES PERFORMANCES

### **Voir les logs JSON avec performance:**
```bash
cat logs/requests/2025-10-14.json | jq '.[] | {request_id, total_time: .metadata.processing_time_ms, llm_cost: .metadata.performance.llm_usage.total_cost_usd}'
```

### **Calculer coût total du jour:**
```bash
cat logs/requests/2025-10-14.json | jq '[.[] | .metadata.performance.llm_usage.total_cost_usd] | add'
```

### **Voir les requêtes les plus lentes:**
```bash
cat logs/requests/2025-10-14.json | jq 'sort_by(.metadata.processing_time_ms) | reverse | .[] | {request_id, time_ms: .metadata.processing_time_ms, message}'
```

### **Comparer 70B vs 8B:**
```bash
# Requêtes 70B
cat logs/requests/2025-10-14.json | jq '[.[] | select(.metadata.performance.llm_usage.model == "llama-3.3-70b-versatile")] | length'

# Requêtes 8B
cat logs/requests/2025-10-14.json | jq '[.[] | select(.metadata.performance.llm_usage.model == "llama-3.1-8b-instant")] | length'
```

## 📈 STATISTIQUES ATTENDUES

### **Temps moyen par étape:**
- `endpoint_init`: ~2ms
- `search_sources`: ~3-5s (MeiliSearch/Supabase)
- `llm_generation`: ~5-10s (70B) ou ~2-4s (8B)
- `response_processing`: ~300ms

### **Coût moyen par requête:**
- **70B:** ~$0.0015 (1.5 millièmes de dollar)
- **8B:** ~$0.0001 (0.1 millième de dollar)

### **Pour 1000 requêtes/jour:**
- **70B:** ~$1.50/jour
- **8B:** ~$0.10/jour

## 🎯 AVANTAGES

✅ **Visibilité totale** sur les performances
✅ **Coûts réels** par requête
✅ **Identification** des goulots d'étranglement
✅ **Optimisation** basée sur données réelles
✅ **Affichage ROUGE** impossible à manquer
✅ **Historique complet** dans logs JSON

## 🔧 PERSONNALISATION

### **Ajouter une nouvelle étape:**
```python
tracker = get_tracker(request_id)
tracker.start_step("ma_nouvelle_etape", custom_param="value")
# ... code ...
tracker.end_step(result_count=42)
```

### **Modifier les couleurs:**
Éditer `rag_performance_tracker.py` ligne ~150:
```python
RED = '\033[91m'  # Rouge
YELLOW = '\033[93m'  # Jaune
GREEN = '\033[92m'  # Vert
```

---

**Créé le:** 2025-10-14
**Version:** 1.0
**Auteur:** Système RAG Performance Tracking
