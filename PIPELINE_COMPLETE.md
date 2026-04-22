# ZETA AI — PIPELINE COMPLÈTE v2.0
> Référence unique. Tout ce qui est déprécié est marqué [LEGACY/SUPPRIMER].
> Tout ce qui est attendu est marqué [ACTIF].

---

## ⚰️ COMPOSANTS DÉPRÉCIÉS — À SUPPRIMER OU METTRE EN LEGACY

| Fichier | Composant | Raison | Action |
|---|---|---|---|
| `core/vector_store_clean.py` | `search_meili_keywords()` | Remplacé par injection directe PRODUCT_INDEX | SUPPRIMER |
| `core/supabase_simple.py` | `search_documents()` PGVector | Remplacé par injection directe CATALOGUE | SUPPRIMER |
| `core/llm_client.py` | `generate_embedding()` | Plus aucun embedding utilisé | SUPPRIMER |
| `core/hyde_optimizer.py` | HYDE entier | Désactivé côté botlive, résiduel sur /chat | SUPPRIMER |
| `core/simplified_rag_engine.py` | `match_products()` VTree + fuzzy | Remplacé par PRODUCT_INDEX injecté | SUPPRIMER bloc |
| `core/simplified_rag_engine.py` | `PREMATCH_DEBUG` path | Inutile si catalogue injecté | SUPPRIMER |
| `tests/amanda_simulator.py` | URL `/chat` | Mauvais endpoint | CORRIGER |
| `core/botlive_prompts_supabase.py` | `plan_type` colonne | Colonne réelle = `plan_name` | CORRIGER |
| `core/amanda_prompt_loader.py` | Pas de guard `isinstance` | Crash si Supabase retourne string | CORRIGER |
| Doc pipeline ancienne | Grille modèles fausse | Pro/Elite = DeepSeek pas Gemma 31B | METTRE À JOUR |

---

## 🏗️ ARCHITECTURE GÉNÉRALE ATTENDUE

```
CLIENT WHATSAPP / TEST
        │
        ▼
┌───────────────────────────────────────┐
│  FastAPI — Rate Limit 300/min         │
│  POST /amandabotlive                  │
│  POST /jessicaragbot                  │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  PYTHON ORCHESTRATEUR (cerveau)       │
│  ├─ Guardian (expiration/quota)       │
│  ├─ Chargement prompt (Redis → Supa)  │
│  ├─ Injection PRODUCT_INDEX           │
│  ├─ Injection CATALOGUE (si identifié)│
│  ├─ Calcul prix (jamais le LLM)       │
│  ├─ §LIVRAISON intercepteur           │
│  └─ Swap catalogue sur tool_call      │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  LLM (raisonnement + langage)         │
│  ├─ Amanda  → Qwen3 235B              │
│  ├─ Jessica A → Gemma 4 26B           │
│  ├─ Jessica S → DeepSeek V3.2         │
│  ├─ Jessica Boost → Gemini Flash Lite │
│  └─ Vision/Insight → Gemini Pro       │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  PYTHON POST-TRAITEMENT               │
│  ├─ Fuzzy XML parser                  │
│  ├─ Extraction slots detection        │
│  ├─ Calcul coût réel                  │
│  ├─ Sauvegarde Supabase               │
│  └─ Notification opérateur            │
└───────────────────────────────────────┘
```

---

## 1. AMANDA BOTLIVE — PIPELINE ATTENDUE

### ÉTAPE 0 — Réception
```
POST /amandabotlive
{company_id, user_id, message, images[]}
request_id = UUID 8 chars
start_time = now()
```

### ÉTAPE 1 — Guardian [ACTIF]
```python
from core.guardian import get_guardian
verdict = guardian.check_access(company_id)
# Si False → réponse humanisée message_registry + stop
# Motifs : ABONNEMENT_EXPIRE | QUOTA_EPUISE | SESSION_LIMIT
```
**Fail-open :** si Guardian crash → log + continuer (jamais bloquer le client)

### ÉTAPE 2 — Chargement Prompt [ACTIF]
```
Ordre de résolution :
1. Redis cache (clé: prompt_bots:amanda:{company_id}, TTL 3600s)
2. Supabase table prompt_bots
3. Fichier local fallback "AMANDA PROMPT UNIVERSEL.md"

Variables injectées (partie DYNAMIQUE uniquement) :
{shop_name}, {wave_number}, {whatsapp_number},
{sav_number}, {support_hours}, {return_policy}, {delai_message}

IMPORTANT : partie statique du prompt en tête = cache prefix max
```

**Guard défensif obligatoire :**
```python
info = pm.get_company_info(company_id)
if isinstance(info, str) or info is None:
    info = {}  # fallback silencieux, jamais crash
```

**Colonne Supabase correcte :**
```python
.select("plan_name, has_boost, status, ...")  # plan_name PAS plan_type
```

### ÉTAPE 3 — Historique [ACTIF]
```python
hist = await get_history(company_id, user_id)
conversation_history = str(hist)[:2000]
# Table: conversations | Limit: 10 messages | Order: DESC
```

### ÉTAPE 4 — Vision OCR (si image) [ACTIF]
```python
if req.images:
    vres = await analyze_product_with_gemini(image_url, message)
    vision_ocr = f"[VISION_OCR: {vres['raw'][:500]}]"
    # Modèle: google/gemini-3.1-flash-lite-preview (produit)
    # Modèle: google/gemini-3.1-pro-preview (paiement Wave)
```

### ÉTAPE 5 — Construction Prompt Final [ACTIF]
```
[SYSTEM_PROMPT statique — cache prefix]
[LOGISTIQUE + SUPPORT dynamiques]
---
## HISTORIQUE
{conversation_history}

[VISION_OCR: ...] (si image)

## MESSAGE CLIENT
{message}
```

### ÉTAPE 6 — Résolution Modèle [ACTIF]
```python
from core.bot_registry import get_amanda_config
cfg = get_amanda_config(plan_name, has_boost)
# Résultat TOUJOURS : qwen/qwen3-235b-a22b-2507
# Boost IGNORÉ pour Amanda (règle business)
# Fallback : google/gemma-4-26b-a4b-it

enforce_allowed_model(model)  # garde-fou
```

### ÉTAPE 7 — Appel LLM [ACTIF]
```python
params = {
    temperature: 0.72,
    frequency_penalty: 0.45,
    presence_penalty: 0.30,
    max_tokens: 350,
    top_p: 0.92
}
llm_result = await llm_client.complete(prompt, model, **params)
```

### ÉTAPE 8 — Parsing XML [ACTIF]
```python
# Fuzzy parser — tolère XML légèrement malformé
thinking = extract_field(raw, "thinking")
response_text = extract_field(raw, "response")
detection_slots = {
    "resume": extract_detection(thinking, "RÉSUMÉ"),
    "zone":   extract_detection(thinking, "ZONE"),
    "telephone": extract_detection(thinking, "TÉLÉPHONE"),
    "paiement":  extract_detection(thinking, "PAIEMENT"),
}
handoff = "true" in extract_field(thinking, "handoff").lower()
         or "##HANDOFF##" in response_text
```

### ÉTAPE 9 — Intercepteur §LIVRAISON [ACTIF]
```python
if "§LIVRAISON" in response_text:
    zone = extract_delivery_zone(detection_slots["zone"])
    if zone.cost and zone.name:
        response_text = response_text.replace("§LIVRAISON", f"{zone.cost}F")
    else:
        # Zone floue → court-circuit Python (pas le LLM)
        response_text = "C'est noté ! Dans quelle commune et quartier précisément ?"
```

### ÉTAPE 10 — Calcul Dossier Complet [ACTIF]
```python
has_article = bool(detection_slots["resume"] or vision_ocr)
has_zone    = bool(detection_slots["zone"])
has_phone   = bool(detection_slots["telephone"])
dossier_complet = has_article and has_zone and has_phone
# Paiement exclu par design Amanda
```

### ÉTAPE 11 — Calcul Coût Réel [ACTIF — À BRANCHER]
```python
from core.cost_calculator import compute_cost
cost = compute_cost(model_name, prompt_tokens, completion_tokens)
# COST_TABLE dans cost_calculator.py — voir BLOC 5
```

### ÉTAPE 12 — Sauvegarde [ACTIF]
```python
await save_message_supabase(company_id, user_id, "user", message)
await save_message_supabase(company_id, user_id, "assistant", response_text)
```

### ÉTAPE 13 — Notification Opérateur [ACTIF]
```python
if handoff or dossier_complet:
    save_operator_notification(company_id, user_id, amanda_summary)
    await send_push_to_company(company_id, "Nouvelle précommande", ...)
```

### ÉTAPE 14 — Réponse API [ACTIF]
```json
{
  "response": "...",
  "detection_slots": {"resume","zone","telephone","paiement"},
  "dossier_complet": true/false,
  "handoff": true/false,
  "model": "qwen/qwen3-235b-a22b-2507",
  "plan": "starter",
  "prompt_tokens": 1340,
  "completion_tokens": 87,
  "cached_tokens": 1100,
  "cost": 0.000095,
  "processing_time_ms": 1200,
  "timings": {
    "prompt_load_ms": 45,
    "history_load_ms": 120,
    "vision_ocr_ms": 0,
    "llm_call_ms": 900,
    "total_endpoint_ms": 1200
  }
}
```

---

## 2. JESSICA RAG BOT — PIPELINE ATTENDUE

### ÉTAPE 0 — Réception
```
POST /jessicaragbot
{company_id, user_id, message, images[]}
```

### ÉTAPE 1 — Guardian [ACTIF]
```python
# Identique Amanda — voir ÉTAPE 1 ci-dessus
```

### ÉTAPE 2 — Plan + Boost [ACTIF]
```python
info = pm.get_company_info(company_id)
plan_name = info.get("plan_name") or "starter"  # plan_name pas plan_type
has_boost = info.get("has_boost", False)
```

### ÉTAPE 3 — Résolution Modèle [ACTIF]
```python
from core.bot_registry import get_jessica_config
cfg = get_jessica_config(plan_name, has_boost)

# GRILLE OFFICIELLE :
# decouverte/starter          → google/gemma-4-26b-a4b-it  (temp 0.45)
# pro/elite (sans boost)      → deepseek/deepseek-v3.2      (temp 0.40)
# tout plan + boost           → gemini-3.1-flash-lite        (temp 0.38)
# image présente              → gemini-3.1-pro-preview       (multimodal)

enforce_allowed_model(model)  # garde-fou
```

### ÉTAPE 4 — Construction Prompt [ACTIF]
```
[SYSTEM_PROMPT Jessica statique — cache prefix]
[DONNÉES DE RÉFÉRENCE dynamiques]
---
[[PRODUCT_INDEX_START]]
Produit 1: {id} | {nom} | variantes: [...]
Produit 2: {id} | {nom} | variantes: [...]
... max 5 produits
[[PRODUCT_INDEX_END]]

[CATALOGUE_START]          ← injecté seulement si produit identifié
{catalogue complet produit X}
[CATALOGUE_END]

[STATUS_SLOTS injecté par Python]
[PRICE_CALCULATION injecté par Python si dispo]
[HISTORIQUE]
[MESSAGE CLIENT]
```

### ÉTAPE 5 — Appel LLM [ACTIF]
```python
llm_result = await llm_client.complete(prompt, model, **cfg["params"])
# params propagés depuis bot_registry — jamais depuis os.getenv()
```

### ÉTAPE 6 — Parsing XML + Fuzzy [ACTIF]
```python
# Extraction tool_call
tool_call = json.loads(extract_field(thinking, "tool_call"))
action = tool_call.get("action")  # NONE | ADD | UPDATE | REPLACE | DELETE | CLARIFY_PIVOT

# Extraction detected_items_json
try:
    items = json.loads(extract_field(thinking, "detected_items_json"))
except json.JSONDecodeError:
    items = []  # failsafe — jamais crash

# Si tool_call contient un product_id nouveau
# → Python swap le CATALOGUE au prochain tour
```

### ÉTAPE 7 — Orchestration Python Post-LLM [ACTIF]
```python
# Python exécute TOUT — le LLM ne fait que raisonner

if action == "ADD":
    order_tracker.add_items(user_id, items)
elif action == "UPDATE":
    order_tracker.update_items(user_id, items)
elif action == "REPLACE":
    order_tracker.replace_items(user_id, items)
elif action == "DELETE":
    order_tracker.delete_items(user_id, items)
elif action == "CLARIFY_PIVOT":
    # Python injecte question binaire A/B directement
    response_text = PIVOT_CLARIFY_TEMPLATE

# Calcul prix — PYTHON UNIQUEMENT
if order_tracker.has_items(user_id) and zone_known:
    price_calc = python_calculate_price(items, zone, catalog)
    # Injecté dans le prochain prompt comme <price_calculation>

# §LIVRAISON intercepteur
if "§LIVRAISON" in response_text:
    response_text = replace_livraison(response_text, zone)

# Swap catalogue si nouveau product_id détecté
if new_product_id := extract_product_id(thinking):
    catalog_to_inject = get_full_catalog(new_product_id)
    # Stocké pour injection au prochain tour
```

### ÉTAPE 8 — Completion Rate [ACTIF]
```python
slots = [has_product, has_variant, has_quantity, has_zone, has_phone, has_payment]
completion_rate = sum(slots) / 6.0

if completion_rate >= 1.0:
    confirmation_code = generate_code()
    order_tracker.set_meta(user_id, "awaiting_confirmation_code", confirmation_code)
    # Prochain message client "oui/ok" → commande confirmée sans LLM
```

### ÉTAPE 9 — Calcul Coût Réel [ACTIF — À BRANCHER]
```python
cost = compute_cost(model_name, prompt_tokens, completion_tokens)
```

### ÉTAPE 10 — Sauvegarde + Réponse [ACTIF]
```json
{
  "response": "...",
  "model": "deepseek/deepseek-v3.2",
  "rank": "RANG_S",
  "plan": "pro",
  "has_boost": false,
  "checklist_state": "3/6",
  "next_step": "DEMANDER_ZONE",
  "prompt_tokens": 11000,
  "completion_tokens": 400,
  "cached_tokens": 8500,
  "cost": 0.00105,
  "processing_time_ms": 3400
}
```

---

## 3. REGISTRY MODÈLES — RÉFÉRENCE ABSOLUE

```python
# core/bot_registry.py — VERSION GRAVÉE

AMANDA = {
    "all_plans": "qwen/qwen3-235b-a22b-2507",   # boost ignoré
    "fallback":  "google/gemma-4-26b-a4b-it",
    "params": {
        "temperature": 0.72, "frequency_penalty": 0.45,
        "presence_penalty": 0.30, "max_tokens": 350, "top_p": 0.92
    }
}

JESSICA = {
    "decouverte": "google/gemma-4-26b-a4b-it",
    "starter":    "google/gemma-4-26b-a4b-it",
    "pro":        "deepseek/deepseek-v3.2",
    "elite":      "deepseek/deepseek-v3.2",
    "boost":      "google/gemini-3.1-flash-lite-preview",
    "fallback":   "google/gemma-4-26b-a4b-it",
    "params_rang_a": {"temperature": 0.45, "frequency_penalty": 0.20,
                      "presence_penalty": 0.15, "max_tokens": 900, "top_p": 0.88},
    "params_rang_s": {"temperature": 0.40, "frequency_penalty": 0.15,
                      "presence_penalty": 0.10, "max_tokens": 900, "top_p": 0.85},
    "params_boost":  {"temperature": 0.38, "frequency_penalty": 0.15,
                      "presence_penalty": 0.10, "max_tokens": 900, "top_p": 0.85},
}

VISION = {
    "ocr_produit":  "google/gemini-3.1-flash-lite-preview",
    "ocr_paiement": "google/gemini-3.1-pro-preview",
    "params_ocr":     {"temperature": 0.10, "max_tokens": 200},
    "params_paiement":{"temperature": 0.05, "max_tokens": 300},
}

INSIGHT = {
    "model":  "google/gemini-3.1-pro-preview",
    "params": {"temperature": 0.60, "max_tokens": 4000},
}

ALLOWED_MODELS = {
    "qwen/qwen3-235b-a22b-2507",
    "google/gemma-4-26b-a4b-it",
    "google/gemma-4-31b-it",
    "deepseek/deepseek-v3.2",
    "google/gemini-3.1-flash-lite-preview",
    "google/gemini-3.1-pro-preview",
}
```

---

## 4. CALCUL COÛT RÉEL — À BRANCHER

```python
# core/cost_calculator.py

COST_TABLE = {
    "qwen/qwen3-235b-a22b-2507":            {"input": 0.071, "output": 0.10},
    "google/gemma-4-26b-a4b-it":            {"input": 0.08,  "output": 0.35},
    "google/gemma-4-31b-it":                {"input": 0.13,  "output": 0.38},
    "deepseek/deepseek-v3.2":               {"input": 0.081, "output": 0.419},
    "google/gemini-3.1-flash-lite-preview": {"input": 0.10,  "output": 0.40},
    "google/gemini-3.1-pro-preview":        {"input": 0.50,  "output": 1.50},
}

def compute_cost(model: str, prompt_tokens: int, completion_tokens: int,
                 cached_tokens: int = 0) -> float:
    rates = COST_TABLE.get(model, {"input": 0.10, "output": 0.40})
    billable_input = prompt_tokens - cached_tokens
    return (
        billable_input    * rates["input"]  +
        cached_tokens     * rates.get("cache_read", rates["input"] * 0.1) +
        completion_tokens * rates["output"]
    ) / 1_000_000

# Cache read rates (OpenRouter providers)
CACHE_READ_TABLE = {
    "google/gemma-4-26b-a4b-it":            0.01,   # DeepInfra
    "deepseek/deepseek-v3.2":               0.0081, # DeepSeek direct
    "google/gemini-3.1-flash-lite-preview": 0.025,
    "google/gemini-3.1-pro-preview":        0.125,
}
```

---

## 5. SIMULATEUR — ENDPOINTS CORRECTS

```bash
# Amanda
CHAT_URL="http://127.0.0.1:8002/amandabotlive" \
  python -m tests.amanda_simulator --http

# Amanda (accès externe)
CHAT_URL="http://194.60.201.228:8002/amandabotlive" \
  python -m tests.amanda_simulator --http

# Jessica
CHAT_URL="http://127.0.0.1:8002/jessicaragbot" \
  python -m tests.jessica_simulator --http
```

**Règle :** En interne (même serveur) → `127.0.0.1`.
Depuis machine distante → `194.60.201.228`.

---

## 6. RÉSUMÉ ÉTAT SYSTÈME

| Composant | État | Action |
|---|---|---|
| Amanda /amandabotlive | 🔴 500 (plan_type bug) | Fix immédiat |
| Jessica /jessicaragbot | 🟡 Fonctionne, mauvais modèle affiché | Fix registry |
| Guardian | 🟢 Actif | OK |
| Redis cache prompt | 🟢 Actif (HIT tour 2) | OK |
| Calcul coût | 🔴 Toujours $0.00 | Brancher cost_calculator |
| Cache tokens | 🔴 Toujours 0 | Lire usage.cache_read_input_tokens |
| HYDE | 🔴 Résiduel sur /chat | Désactiver |
| Meilisearch | 🔴 Déprécié actif | Supprimer |
| PGVector/Embeddings | 🔴 Déprécié actif | Supprimer |
| PRODUCT_INDEX | 🟢 Actif | OK |
| CATALOGUE swap | 🟢 Actif | OK |
| Fuzzy XML parser | 🟢 Actif | OK |
| Simulateur Amanda URL | 🔴 Mauvais endpoint | Corriger |